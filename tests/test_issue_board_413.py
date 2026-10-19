# -*- coding: utf-8 -*-
"""Issue #413: Save changes kan altid naas i redigeringspanelet.

Kroppens hoejde i sidepanelet skal traekke HELE det faste fra (hovedet,
stregen, foden og luften imellem). Foer stod foden uden parentes, saa dens
hoejde blev lagt til pladsen, og med "Add more details" foldet ud skubbede
kroppen Save changes ud under panelets kant."""
import os
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Issue Board", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import ib_parts as P  # noqa: E402


def _walk(nodes):
    for n in nodes:
        yield n
        yield from _walk(n.children)


def _form():
    return {c.name: c for c in _walk(P.build_form())}


def test_modal_order_head_body_rule_foot():
    form = _form()
    modal = form["conIbFormModal"]
    assert [c.name for c in modal.children] == [
        "conIbFormHead", "conIbFormBody", "conIbFormFootRule", "conIbFormFoot"]
    assert modal.props["Height"] == "App.Height"
    assert modal.props["LayoutOverflowY"] == "LayoutOverflow.Hide"
    body = form["conIbFormBody"]
    assert body.props["LayoutOverflowY"] == "LayoutOverflow.Scroll"
    # Administration og Resolution ligger i det, der scroller - Save i foden.
    names = {c.name for c in _walk([body])}
    assert {"conIbFormMore", "conIbManage", "inpIbResolution"} <= names
    assert "btnIbFormSubmit" in {c.name for c in _walk([form["conIbFormFoot"]])}
    assert "btnIbFormSubmit" not in names


def test_body_room_subtracts_all_fixed_parts():
    form = _form()
    head, rule, foot = form["conIbFormHead"], form["conIbFormFootRule"], form["conIbFormFoot"]
    fixed = f"({head.h}) + {P.POP_GAP} + ({rule.h}) + {P.POP_GAP} + ({foot.h})"
    # Sidepanelet er App.Height hoejt uden margen: polstring + et gap + det faste.
    room = f"App.Height - {2 * P.POP_PAD} - {P.POP_GAP} - ({fixed})"
    assert form["conIbFormBody"].props["Height"].endswith(f", {room}))")
    # Luft forneden, saa det sidste felt ikke staar klemt mod foden.
    assert form["conIbFormBody"].props["PaddingBottom"] == "8"


def test_details_toggle_keeps_values():
    # Fold ud/ind skifter kun synligheden - intet nulstilles.
    more = _form()["btnIbMore"].props["OnSelect"]
    assert more == "Set(varIbMore, !varIbMore)"
    assert _form()["conIbFormMore"].props["Visible"] == "varIbMore"
