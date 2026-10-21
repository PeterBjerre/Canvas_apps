# -*- coding: utf-8 -*-
"""
Issue #492: "Message SAP maintenance" - beskedfeltet starter tomt med en
pladsholder, og kanten paa "Subject or request" (knappen, den udfoldede
liste og soegefeltet) klippes ikke af foraelderen.

    python3 -m pytest tests/test_feedback_message_492.py
"""
import glob
import os

import yaml

from conftest import ROOT
import feedback_popup as fb

PLACEHOLDER = "Describe your question, idea or issue..."


def _screens():
    return {os.path.basename(p): yaml.safe_load(open(p, encoding="utf-8"))
            for p in glob.glob(os.path.join(ROOT, "BIO SAP App", "Screen*.pa.yaml"))}


def _find(node, ctrl):
    if isinstance(node, dict):
        if ctrl in node and isinstance(node[ctrl], dict) and "Control" in node[ctrl]:
            return node[ctrl]
        node = list(node.values())
    if isinstance(node, list):
        for x in node:
            hit = _find(x, ctrl)
            if hit is not None:
                return hit
    return None


def _prefix(doc, name):
    """Skaermens praefiks fra navnet paa Message-feltet (inp<p>FbMessage)."""
    for p in ("Eq", "Fl", "Ib", "Kks", "Mat", "Md", "Mp", "Vhp"):
        if _find(doc, f"inp{p}FbMessage") is not None:
            return p
    raise AssertionError(name)


def _props(doc, ctrl):
    c = _find(doc, ctrl)
    assert c is not None, ctrl
    return {k: str(v).lstrip("=") for k, v in c["Properties"].items()}


def test_message_starts_empty_with_the_placeholder():
    screens = _screens()
    assert len(screens) >= 8
    for name, doc in screens.items():
        p = _prefix(doc, name)
        props = _props(doc, f"inp{p}FbMessage")
        assert props["Default"] == '""', name
        assert props["Placeholder"] == f'"{PLACEHOLDER}"', name
    text = "".join(open(f, encoding="utf-8").read()
                   for f in glob.glob(os.path.join(ROOT, "BIO SAP App", "Screen*.pa.yaml")))
    for gone in ("Hello SAP Maintenance Team", "Kind regards,", "Write your message"):
        assert gone not in text, gone


def test_subject_border_has_room_on_every_side():
    e = str(fb.EDGE)
    assert fb.EDGE > 0
    for name, doc in _screens().items():
        p = _prefix(doc, name)
        # Knappen med kanten staar i en ramme med luft til siderne og forneden.
        frame = _props(doc, f"con{p}FbSubjectFrame")
        assert (frame["PaddingLeft"], frame["PaddingRight"], frame["PaddingBottom"]) == (e, e, e), name
        assert "BorderColor" in _props(doc, f"con{p}FbSubject"), name
        # Den udfoldede liste: luft paa alle fire sider inde i sin ramme.
        layer = _props(doc, f"con{p}FbSubjectLayer")
        for side in ("Top", "Right", "Bottom", "Left"):
            assert layer["Padding" + side] == e, (name, side)
        assert layer["Visible"] == fb.PICK, name
        lst = _props(doc, f"con{p}FbSubjectList")
        assert "Visible" not in lst and lst["BorderThickness"] == "1", name
        # Soegefeltet har luft til siderne og foroven.
        find = _props(doc, f"con{p}FbSubjectFind")
        for side in ("Top", "Right", "Left"):
            assert find["Padding" + side] == e, (name, side)


def test_list_sits_below_the_subject_cell_on_every_device():
    """Listen startede ved et fast Y = 66, mens cellen er 20 + 6 + H.control
    (44 paa touch) - listen daekkede knappens bundkant paa tablet/mobil."""
    for name, doc in _screens().items():
        p = _prefix(doc, name)
        cell_h = _props(doc, f"con{p}FbSubjectCell")["Height"]
        assert "H.control" in cell_h, name
        layer = _props(doc, f"con{p}FbSubjectLayer")
        assert layer["Y"] == cell_h, name
        assert layer["X"] == "0" and layer["Width"] == "Parent.Width", name


def _eval(expr, control, rank=3, app_h=900):
    expr = (expr.replace("H.control", str(control))
            .replace("LayoutRank", str(rank)).replace("App.Height", str(app_h)))
    expr = expr.replace("If(", "_if(")
    return eval(expr, {"_if": lambda c, a, b: a if c else b, "Max": max, "Min": min})


def test_open_list_stays_inside_the_area():
    """Den hoejeste liste (fuld soegning og galleri) slutter senest ved
    omraadets bund - ogsaa paa touch, hvor H.control er 44."""
    for name, doc in _screens().items():
        p = _prefix(doc, name)
        area_h = _props(doc, f"con{p}FbArea")["Height"]
        layer = _props(doc, f"con{p}FbSubjectLayer")
        y = layer["Y"]
        h = (layer["Height"].replace(f"Min(gal{p}FbSubject.AllItemsCount, 7) * 36", "10000")
             .replace("CountRows(colFbRequests) > 6", "True"))
        for control, rank in ((36, 3), (44, 2), (44, 1)):
            for app_h in (700, 900, 1200):
                top = _eval(y, control, rank, app_h)
                bottom = top + _eval(h, control, rank, app_h)
                assert bottom <= _eval(area_h, control, rank, app_h) + 0.01, (name, control, rank, app_h)
                assert top == _eval(_props(doc, f"con{p}FbSubjectCell")["Height"], control, rank, app_h)
