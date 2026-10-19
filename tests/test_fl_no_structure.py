# -*- coding: utf-8 -*-
"""Issue #432: Structure-sektionen er fjernet fra Functional Location.

Skaermen er den samme i Create, Draft, Edit og View, saa een skaerm
daekker alle fire. Testen laaser, at kortet, dets overskrift, forklaring,
HTML-tabel og tom-tekst er vaek, at kroppen ikke reserverer plads til det,
og at Rows og Classes samt de data, KKS-valideringen og klassetildelingen
bruger, stadig er der.

    python3 -m pytest tests/test_fl_no_structure.py
"""
import os
import re

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenFunctionalLocation.pa.yaml")
PARTS = os.path.join(ROOT, "Functional Location App", "build", "fl_parts.py")
ASSEMBLE = os.path.join(ROOT, "Functional Location App", "build", "assemble_screen.py")


def _text(p):
    return open(p, encoding="utf-8").read()


def test_structure_controls_are_gone_from_the_screen():
    text = _text(SCREEN)
    for name in ("conFlStructCard", "txtFlStructH", "txtFlStructSub",
                 "htmFlStructure", "txtFlStructNone"):
        assert name not in text, name
    assert '="Structure"' not in text
    assert "to see its structure" not in text
    assert "The KKS keys the rules read" not in text
    # Structure var skaermens eneste HtmlViewer.
    assert "Control: HtmlViewer" not in text


def test_builder_no_longer_builds_the_section():
    assert "build_structure" not in _text(PARTS)
    assert "structure_html" not in _text(PARTS)
    assert "build_structure" not in _text(ASSEMBLE)


def test_rows_classes_and_their_data_are_kept():
    text = _text(SCREEN)
    for name in ("conFlRowsCard", "galFlRows", "btnFlVerify",
                 "conFlClassesCard"):
        assert re.search(r"- %s:\n" % name, text), name
    # Raekkerne, valideringen og klasserne laeses stadig fra de samme samlinger.
    for col in ("colFlRows", "colFlIssues", "AssignedClass"):
        assert col in text, col
