# -*- coding: utf-8 -*-
"""Issue #489: Activity-cellen i Issue Boards oversigt er en taleboble med
tallet INDENI - ikke et frit tal. 0 er en dempet streg-boble, over 0 en
fyldt boble i primaerfarven, over 99 staar "99+". Hele boblen er een
klikflade (hover, tryk, fokus), der aabner sagen paa fanen Activity som
papirclipsen aabner Attachments - baade i tabellen og i det kompakte kort."""
import os
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Issue Board", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import ib_parts as P  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml")


def _walk(ctrls):
    for c in ctrls:
        yield c
        yield from _walk(getattr(c, "children", []) or [])


def _list():
    return {c.name: c for c in _walk([P.build_list()])}


def test_count_is_drawn_inside_a_speech_bubble():
    img = P.ROW_ACT_IMG
    assert img.count("<path d='M7 1 H25") == 2          # boblen med hale, begge tilstande
    assert img.count("text-anchor='middle'") == 2       # tallet centreret i boblen
    assert img.count('" & s & "') == 2
    assert 'If(n > 99, "99+", Text(n))' in img
    muted, accent = img.split("If(n = 0,")[1].split("<svg")[1:3]
    assert "fill='none'" in muted and "hex-text-muted" in muted
    assert "hex-color-brand-primary" in accent and "hex-text-on-primary" in accent
    # Opslaget staar een gang.
    assert img.count("LookUp(colIbActN") == 1


def test_whole_bubble_is_one_action_on_both_layouts():
    ctrls = _list()
    for suffix in ("", "C"):
        b = ctrls[f"btnIbRowAct{suffix}"]
        assert b.control == "Image"
        assert b.props["Image"] == P.ROW_ACT_IMG
        assert b.props["OnSelect"] == P.OPEN_ROW_ACT
        assert b.props["Visible"] == P.ROW_SEE_ACT
        assert b.props["TabIndex"] == "0"
        assert b.props["HoverFill"] != b.props["Fill"]
        assert b.props["PressedFill"] != b.props["Fill"]
        assert b.props["FocusedBorderThickness"] == "2"
        assert "Show the activity on" in b.props["AccessibleLabel"]
        assert ctrls[f"conIbRowAct{suffix}"].children == [b]
    # Resten af raekken aabner stadig Description.
    assert ctrls["btnIbRowOpen"].props["OnSelect"] == P.OPEN_ROW
    assert 'Set(varIbTab, "details")' in P.OPEN_ROW


def test_generated_screen_has_the_bubble():
    text = open(SCREEN, encoding="utf-8").read()
    for name in ("btnIbRowAct", "btnIbRowActC"):
        block = text.split(f"- {name}:")[1].split("\n    - ")[0]
        assert "Control: Image" in block
        assert "99+" in block
