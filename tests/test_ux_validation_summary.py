# -*- coding: utf-8 -*-
"""Hvad mangler, og hvor (UX-review 2026-10, M4)."""
import os

import build_helpers as bh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "BIO SAP App")


def _yaml(screen):
    return open(os.path.join(APP, screen), encoding="utf-8").read()


def _block(y, name, n=4000):
    i = y.index(f"- {name}:")
    return y[i:i + n]


def test_the_summary_is_a_list_with_one_go_button_per_item():
    g = bh.validation_summary("X", "colXBad", "ThisItem.Key", "Open row", "Select(Parent)",
                              '"2 to fix"', "varXFix", "Set(varXFix, false)")
    head, gal = g.children
    assert g.props["Visible"] == "varXFix"
    assert [c.name for c in head.children] == ["txtXFixTitle", "btnXFixClose"]
    assert gal.control == "Gallery" and gal.props["Items"] == "colXBad"
    txt, go = gal.children
    assert go.props["OnSelect"] == "Select(Parent)"
    assert '"Open row: " & ThisItem.Key' == go.props["AccessibleLabel"]
    # Hoejst FIX_ROWS_MAX raekker - saa scroller listen.
    assert f"{bh.FIX_ROWS_MAX}" in gal.props["Height"]


def test_domains_show_draft_rows_before_submit_with_go_to_field():
    for screen, tag in (("ScreenEquipment.pa.yaml", "Eq"), ("ScreenMaterial.pa.yaml", "Mat"),
                        ("ScreenMeasuringPoint.pa.yaml", "Mp")):
        y = _yaml(screen)
        fix = _block(y, f"con{tag}Fix")
        assert "Still missing" in y and "!var%sViewOnly" % tag in fix
        go = _block(y, f"btn{tag}FixGo")
        assert f"Set(var{tag}ActiveRowId, ThisItem.RowId)" in go, screen


def test_vh_missing_list_has_go_to_buttons_that_highlight_the_section():
    y = _yaml("ScreenVhPlan.pa.yaml")
    for name, step in (("Plan", 1), ("Item", 2), ("Ops", 3)):
        b = _block(y, f"btnVhpMissing{name}Go", 2500)
        assert "Set(varVhpMissingOn, false)" in b
        assert f"Set(varVhpFocusStep, {step})" in b
