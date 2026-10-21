# -*- coding: utf-8 -*-
"""Issue #503: kommentarfeltet i Activity starter med plads til tre linjer
og vokser uden loft (ingen scrollbar i feltet), og kortene og
Description-fladerne i sidepanelet faar ikke klippet deres kanter."""
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


def _pad(ctrl):
    return [int(ctrl.props.get(f"Padding{s}", "0")) for s in ("Top", "Right", "Bottom", "Left")]


def test_comment_field_starts_at_three_lines_and_has_no_ceiling():
    P, c = _ctrls()
    h = c["conIbCommentBox"].props["Height"]
    assert P.COMMENT_LINES == 3
    assert f"{P.COMMENT_LINES} * (If(LayoutRank < 2, 22, 20))" in h
    # Intet loft: kun Max - feltet viser altid hele teksten, og fanen
    # (ikke feltet) scroller, naar det bliver hoejt.
    assert "Min(" not in h.replace("Min(560", "")
    assert not hasattr(P, "COMMENT_MAX_H")
    assert c["conIbDetActivity"].props["LayoutOverflowY"] == "LayoutOverflow.Scroll"
    # Feltet er stadig nederst i fanen med send-ikonet nederst til hoejre,
    # og Internal note og hjaelpeteksten lige under.
    assert c["inpIbComment"].props["Height"] == "Parent.Height"
    assert c["btnIbPost"].props["Y"].startswith("Parent.Height - Self.Height")
    assert [k.name for k in c["conIbComposer"].children] == [
        "conIbCommentBox", "chkIbInternal", "txtIbCommentHint"]


def test_cards_and_tabs_have_air_to_the_edge_of_the_top():
    P, c = _ctrls()
    top = c["conIbDetTop"]
    assert _pad(top) == [P.EDGE] * 4
    assert top.props["LayoutOverflowX"] == "LayoutOverflow.Hide"
    # Kortenes kant er med i polstringen, og deres indre bredde passer.
    for name in ("conIbDetInfo", "conIbDetFacts"):
        card = c[name]
        assert card.props["BorderThickness"] == "1"
        assert _pad(card) == [P.CARD_PAD + P.BORDER] * 4
    assert P.TOP_IN == P.DET_BODY_W
    assert P.CARD_IN == f"({P.TOP_IN} - {2 * (P.CARD_PAD + P.BORDER)})"


def test_content_has_the_same_side_margins_as_the_top():
    P, c = _ctrls()
    content = c["conIbDetContent"]
    assert _pad(content) == [0, P.EDGE, 0, P.EDGE]
    # Fanernes bredder regnes af den samme bredde som toppens.
    assert P.DET_BODY_W == f"({P.DETAIL_PANEL_IN} - {2 * P.EDGE})"
    assert P.DET_IN == f"({P.DET_BODY_W} - {P.lay.SCROLLBAR_W})"


def test_description_boxes_keep_their_whole_border():
    P, c = _ctrls()
    for name in ("IbDetDesc", "IbDetSteps", "IbDetExpected", "IbDetActual"):
        col, box, body = c[f"con{name}Body"], c[f"con{name}Box"], c[f"txt{name}"]
        # Luft i kolonnen til venstre, hoejre og forneden - fladen staar
        # ikke ude ved den kant, der skjuler overloebet.
        assert _pad(col) == [0, P.EDGE, P.EDGE, P.EDGE], name
        assert box.props["Width"] == P.BOX_W, name
        # Kanten er med i polstringen (og dermed i hoejden), lige meget
        # over og under, saa teksten staar midt i fladen.
        t, r, b, l = _pad(box)
        assert t == b == P.BOX_PAD_Y + P.BORDER, name
        assert r == l == P.BOX_PAD_X + P.BORDER, name
        assert box.props["Height"].startswith(f"{2 * (P.BOX_PAD_Y + P.BORDER)} + "), name
        # Hoejden foelger den ombrudte tekst - fladen vokser med den.
        assert "Len(t)" in box.props["Height"] and body.props["Wrap"] == "true", name
        assert body.props["Width"] == P.BOX_TEXT_W, name
        # Kolonnens hoejde er etiketten, luften, fladen og bundluften.
        assert col.props["Height"].startswith(f"{P.BLOCK_TITLE_H + P.EDGE} + 6 + "), name
