# -*- coding: utf-8 -*-
"""Issue #499: kommentarfeltet i Activity vokser opad med teksten, og
handlingsknapperne (Edit, Archive, Delete) klippes ikke i sidepanelet."""
import os
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Issue Board", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def _walk(nodes):
    for n in nodes if isinstance(nodes, list) else [nodes]:
        yield n
        yield from _walk(n.children or [])


def _ctrls():
    import ib_parts as P
    return P, {c.name: c for c in _walk(P.build_detail())}


def test_comment_box_grows_with_the_text_between_a_min_and_a_max():
    P, c = _ctrls()
    box, field = c["conIbCommentBox"], c["inpIbComment"]
    h = box.props["Height"]
    # Hoejden foelger teksten (linjeskift og laengde), med loft og bund.
    assert "inpIbComment.Text" in h and "Char(10)" in h
    assert h.startswith("Min(") and f"Min({P.COMMENT_MAX_H}," in h
    assert "H.hit + 8" in h
    # Loftet foelger fanens plads - ingen kontrol-til-kontrol hoejdereference.
    assert "App.Height" in h and ".Height" not in h.replace("App.Height", "")
    # Feltet fylder boksen; send-ikonet staar fast nederst til hoejre.
    assert field.props["Height"] == "Parent.Height"
    assert field.props["Type"] == "TextInputType.Multiline"
    assert field.props["TriggerOutput"] == "TriggerOutput.Keypress"
    assert c["btnIbPost"].props["Y"].startswith("Parent.Height - Self.Height")
    # Feeden over faar resten: den traekker feltets hoejde fra.
    assert h in c["conIbActFeed"].props["Height"]
    assert h in c["conIbComposer"].props["Height"]
    # Internal note og hjaelpeteksten staar stadig lige under feltet.
    assert [k.name for k in c["conIbComposer"].children] == [
        "conIbCommentBox", "chkIbInternal", "txtIbCommentHint"]


def test_action_row_is_tall_enough_and_not_centre_shifted():
    P, c = _ctrls()
    row = c["conIbDetActions"]
    assert row.props["Height"] == P.ACT_ROW_H
    assert row.props["PaddingTop"] == row.props["PaddingBottom"] == str(P.ACT_PAD)
    assert row.props["LayoutAlignItems"] == "LayoutAlignItems.Start"
    assert row.props["AlignInContainer"] == "AlignInContainer.Start"
    # Ikke skjult som loesning: raekken er knaphoejden + luft.
    for n in ("btnIbReopen", "btnIbEdit", "btnIbArchive", "btnIbRestore", "btnIbDelete"):
        b = c[n]
        assert b.props["AlignInContainer"] == "AlignInContainer.Start", n
        assert int(b.props["Height"]) == P.ICON_BTN, n
    # Linjen med status og knapperne er lige saa hoej som knapraekken.
    assert P.ACT_ROW_H in c["conIbDetMeta"].props["Height"]
    # Handlingerne og deres synlighed er uaendrede.
    assert c["btnIbEdit"].props["Visible"] == "IbCanEdit"
    assert c["btnIbDelete"].props["Visible"] == "IbCanManage"
    assert row.props["Visible"] == P.CAN_ACT
