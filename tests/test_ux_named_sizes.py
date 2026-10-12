# -*- coding: utf-8 -*-
"""Navngivne stoerrelser T og R i App.Formulas (UX-review 2026-10, M6)."""
import glob
import os
import re

import importlib.util

import layout_tokens as lay

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _check_layout():
    """tools/check_layout.py via stien - flere tests laegger en app's
    build-mappe (med sin egen check_layout.py) forrest i sys.path."""
    spec = importlib.util.spec_from_file_location(
        "tools_check_layout", os.path.join(ROOT, "tools", "check_layout.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_t_and_r_are_the_type_scale_and_the_radii():
    assert lay.named_constant("T", lay.SIZE_BODY) == "T.body"
    assert lay.named_constant("T", lay.SIZE_PAGE_TITLE) == "T.pageTitle"
    assert lay.named_constant("R", lay.RADIUS_CARD) == "R.card"
    assert lay.named_constant("T", 15) is None
    f = lay.formula()
    assert "T = {" in f and "R = {" in f
    # check_layout kan regne paa dem.
    assert lay.named_value("T", "body", 1366) == lay.SIZE_BODY


def test_the_screens_name_every_size_on_the_scale():
    for path in glob.glob(os.path.join(ROOT, "BIO SAP App", "Screen*.pa.yaml")):
        y = open(path, encoding="utf-8").read()
        # Ingen Size er et rent tal (regel 42) ...
        assert not re.search(r"\n\s+Size: \|-\n\s+=\d+\n", y), path
        # ... og navnene bruges.
        assert "=T.body" in y or "=T.input" in y, path


def test_rule_42_flags_an_off_scale_size():
    class Ctx:
        problems = []
        all_nodes = [("p", "txtXOdd", {"Control": "ModernText", "Properties": {"Size": "=15"}}),
                     ("p", "txtXOk", {"Control": "ModernText", "Properties": {"Size": "=T.body"}})]
    _check_layout().rule_42(Ctx)
    assert len(Ctx.problems) == 1 and "txtXOdd" in Ctx.problems[0]
