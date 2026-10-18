# -*- coding: utf-8 -*-
"""
Issue #361: Long text-udsnittet i operationsraekken staar paa een linje.
Linjeskift bliver til mellemrum, teksten afkortes med "...", knappen har
samme 12 px skrift som de andre knapper i raekken, og "Add text..." og
klikket, der aabner long text-popup'en, er uaendret.

    python3 -m pytest tests/test_vhp_longtext_one_line.py
"""
import os
import re

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")


def _block(text, name):
    m = re.search(r"\n(\s+)- %s:\n" % name, text)
    assert m, name + " mangler"
    indent = m.group(1)
    rest = text[m.end():]
    end = re.search(r"\n%s- \w+:\n" % indent, rest)
    return rest[:end.start()] if end else rest


def _prop(block, prop):
    m = re.search(r"\n(\s+)%s: \|-\n((?:\1\s+.*\n?)+)" % prop, block)
    return m.group(2) if m else ""


def test_row_preview_is_single_line_and_truncated():
    b = _block(open(SCREEN, encoding="utf-8").read(), "btnVhpOpLongText")
    txt = _prop(b, "Text")
    assert "Char(10)" in txt and "Char(13)" in txt
    assert '"Add text..."' in txt
    assert 'If(Len(lt) > 12, Left(lt, 12) & "...", lt)' in txt
    assert "=T.small" in _prop(b, "Size")
    # Kolonnebredde, hoejde, ikon og klik er uaendret.
    assert "=170" in _prop(b, "Width")
    assert "=32" in _prop(b, "Height")
    assert "DocumentText" in _prop(b, "Icon")
    assert "Set(varVhpLongTextOpen, true)" in _prop(b, "OnSelect")


def test_modal_preview_is_single_line_too():
    b = _block(open(SCREEN, encoding="utf-8").read(), "btnVhpOpMLongText")
    txt = _prop(b, "Text")
    assert "Char(10)" in txt and '"Add text..."' in txt
    assert "Set(varVhpLongTextOpen, true)" in _prop(b, "OnSelect")
