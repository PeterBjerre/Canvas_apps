# -*- coding: utf-8 -*-
"""Functional Location: headeren staar oeverst paa alle skaermbredder (issue #392).

Rammen er lodret, saa raekkefoelgen af dens boern ER placeringen:
[conFlHeader, conFlBody]. Breadcrumb, titel, beskrivelse og knapperne
(New request, Save draft, Submit) staar i headeren - ogsaa under Desktop,
hvor UX-review M8's bundbjaelke foer viste Save draft og Submit nederst.

    python3 -m pytest tests/test_fl_header_top.py
"""
import os
import sys

import yaml

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenFunctionalLocation.pa.yaml")
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)


def _screen():
    doc = yaml.safe_load(open(SCREEN, encoding="utf-8"))
    return list(doc["Screens"].values())[0]


def _find(nodes, name):
    for it in nodes or []:
        (n, body), = it.items()
        if n == name:
            return body
        hit = _find(body.get("Children"), name)
        if hit is not None:
            return hit
    return None


def _kids(body):
    return [list(it)[0] for it in body.get("Children") or []]


def _p(body, key):
    return str((body.get("Properties") or {}).get(key, "")).lstrip("=").strip()


def test_header_is_the_first_child_of_the_vertical_frame():
    scr = _screen()
    (first, root), = scr["Children"][0].items()
    assert first == "conFlRoot"
    assert _p(root, "LayoutDirection") == "LayoutDirection.Vertical"
    # Headeren foerst, kroppen under den - og intet efter kroppen.
    assert _kids(root) == ["conFlHeader", "conFlBody"]
    # Kroppen scroller; headeren har en fast hoejde og flytter sig ikke.
    body = _find(scr["Children"], "conFlBody")
    assert _p(body, "LayoutOverflowY") == "LayoutOverflow.Scroll"
    assert _p(_find(scr["Children"], "conFlHeader"), "FillPortions") == "0"
    # Ingen Y-koordinater inde i rammen - placeringen er layoutets.
    for name in ("conFlHeader", "conFlBody"):
        assert "Y" not in (_find(scr["Children"], name).get("Properties") or {}), name


def test_rows_classes_and_structure_are_in_the_body_below_the_header():
    body = _find(_screen()["Children"], "conFlBody")
    assert _kids(body) == ["conFlRowsCard", "conFlClassesCard", "conFlStructCard"]


def test_breadcrumb_title_description_and_actions_are_in_the_header():
    head = _find(_screen()["Children"], "conFlHeader")
    for name in ("conFlCrumb", "txtFlTitle", "txtFlSub",
                 "btnFlNew", "btnFlSaveDraft", "btnFlSubmit"):
        assert _find(head.get("Children"), name) is not None, name


def test_no_bottom_bar_hides_the_header_actions():
    scr = _screen()
    assert _find(scr["Children"], "conFlFoot") is None
    for name in ("btnFlSaveDraft", "btnFlSubmit"):
        vis = _p(_find(scr["Children"], name), "Visible")
        # Ikke skjult under Desktop (M8 satte "LayoutRank >= 3").
        assert "LayoutRank" not in vis, (name, vis)
    # Kroppen giver ikke laengere plads til en bundbjaelke.
    assert "If(LayoutRank < 3, 60, 0)" not in _p(_find(scr["Children"], "conFlBody"), "Height")


def test_check_layout_rejects_a_frame_with_the_body_first():
    """Regel 23d fanger en ramme, hvor headeren ikke er foerst."""
    import check_layout as cl
    scr = _screen()
    root = scr["Children"][0]["conFlRoot"]
    root["Children"] = list(reversed(root["Children"]))

    class Ctx:
        problems = []
        screen = scr

        @staticmethod
        def _num(*a):
            return 0
    cl.rule_23(Ctx)
    assert any(p.startswith("[23d]") for p in Ctx.problems), Ctx.problems
