# -*- coding: utf-8 -*-
"""Issue #475: Issue Boards sidepanel efter mockupperne.

Status og handlingerne paa een linje under hovedet; Issue information og
Ticket details som to kort med ikoner; rapportoeren een gang med sit eget
personikon (ingen initial-avatar); tre faner, der deler bredden; sektioner
med ikoner i Description; Activity-linjer med et ikon for hvem, forfatter,
type, tid og indhold; kommentarfeltet fast i bunden under en feed, der
scroller for sig selv."""
import os
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Issue Board", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml")


def _walk(nodes):
    for n in nodes if isinstance(nodes, list) else [nodes]:
        yield n
        yield from _walk(n.children or [])


def _ctrls():
    import ib_parts as P
    return P, {c.name: c for c in _walk(P.build_detail())}


def _under(c, root):
    return {k.name for k in _walk(c[root])}


def test_status_and_actions_share_the_line_under_the_header():
    P, c = _ctrls()
    assert [k.name for k in c["conIbDetMeta"].children] == ["bdgIbDetStatus", "conIbDetActions"]
    assert c["conIbDetActions"].props["LayoutJustifyContent"] == "LayoutJustifyContent.End"
    # Telefonens titel i hele bredden (issue #508) staar kun paa mobil.
    top = [k.name for k in c["conIbDetTop"].children if k.name != "txtIbDetTitleM"]
    assert top[0] == "conIbDetMeta" and top[-1] == "conIbDetTabs"
    assert "conIbDetRule" not in c


def test_two_cards_with_icons_and_the_right_facts():
    P, c = _ctrls()
    for card, title, facts in (
            ("conIbDetInfo", "txtIbDetInfoTitle", ("IbDetApp", "IbDetSection", "IbDetPriority")),
            ("conIbDetFacts", "txtIbDetFactsTitle",
             ("IbFactReporter", "IbFactAssigned", "IbFactSeverity", "IbFactReported",
              "IbFactUpdated"))):
        box = c[card]
        assert box.props["BorderColor"] == P.C_CARD_BORDER and box.props["Fill"] == P.C_CARD_BG
        names = _under(c, card)
        assert title in names and f"img{title[3:]}Icon" in names
        for f in facts:
            cell = c[f"con{f}"]
            assert cell.variant == "ManualLayout", f
            icon = c[f"img{f}"]
            assert icon.control == "Image" and icon.props["TabIndex"] == "0", f
            assert icon.props["AccessibleLabel"], f
    # Application har sit eget farvede ikon - det samme som i listen.
    assert P.APP_ICONS in c["imgIbDetApp"].props["Image"]
    # Prioriteten staar stadig som sit maerke i Issue information.
    assert "bdgIbDetPriority" in _under(c, "conIbDetPriority")


def test_requester_once_with_distinct_person_icons():
    P, c = _ctrls()
    texts = [k.props.get("Text", "") for k in c.values()]
    rep = P.REPORTER_FX.format(r="varIbSel")
    # Rapportoerens id staar een gang i hele panelet - ingen avatar med
    # initialerne ved siden af.
    assert texts.count(rep) == 1
    facts = _under(c, "conIbDetFacts")
    assert not [n for n in facts if "Avatar" in n or "Initials" in n]
    req, asg = c["imgIbFactReporter"].props["Image"], c["imgIbFactAssigned"].props["Image"]
    assert req != asg
    # Tildelt CLAUDE: CLAUDE-gnisten i stedet for personen.
    assert asg.startswith('If(varIbSel.AssignedEmail = "claude", ')
    assert P.CLAUDE_TILE in asg


def test_tabs_share_the_full_width():
    P, c = _ctrls()
    w = {c[n].props["Width"] for n in ("btnIbTabDetails", "btnIbTabActivity", "btnIbTabFiles")}
    assert w == {f"({P.TOP_IN} - 16) / If(IbSeeActivity, 3, 2)"}


def test_description_sections_have_icons():
    P, c = _ctrls()
    for name in ("IbDetDesc", "IbDetSteps", "IbDetExpected", "IbDetActual"):
        icon = c[f"img{name}Icon"]
        assert icon.control == "Image" and icon.props["Image"].startswith('"data:image/svg+xml')
        assert c[f"txt{name}Label"].props["FontWeight"] == "FontWeight.Semibold"
    labels = [c[f"txt{n}Label"].props["Text"] for n in ("IbDetDesc", "IbDetSteps",
                                                         "IbDetExpected", "IbDetActual")]
    assert labels == ['"Description"', '"Steps to reproduce"', '"Expected result"',
                      '"Actual result"']


def test_activity_rows_have_identity_author_type_time_and_content():
    P, c = _ctrls()
    gal = c["galIbActivity"]
    assert [k.name for k in gal.children] == ["txtIbActBg", "imgIbActWho", "txtIbActYou",
                                              "txtIbActActor", "txtIbActKind", "txtIbActWhen",
                                              "txtIbActBody"]
    who, you = c["imgIbActWho"], c["txtIbActYou"]
    # Initialerne kun paa dine egne linjer - de andre har et ikon.
    assert you.props["Visible"].startswith('(ThisItem.Actor = "You"')
    assert who.props["Visible"] == "!" + you.props["Visible"]
    # CLAUDE-aktivitet har CLAUDE-gnisten.
    assert who.props["Image"].startswith('If((ThisItem.Actor = "CLAUDE"')
    assert P.CLAUDE_TILE in who.props["Image"]
    assert c["txtIbActActor"].props["Text"] == "ThisItem.Actor"
    assert "internal note" in c["txtIbActKind"].props["Text"]
    assert c["txtIbActWhen"].props["Text"].startswith("Text(ThisItem.At")
    assert c["txtIbActBody"].props["Text"] == "ThisItem.Body"


def test_comment_field_stays_at_the_bottom_under_a_scrolling_feed():
    P, c = _ctrls()
    act = c["conIbDetActivity"]
    assert [k.name for k in act.children] == ["txtIbActState", "conIbActFeed", "txtIbPosted",
                                              "conIbPostFailed", "conIbComposer",
                                              "txtIbArchivedHint"]
    feed = c["conIbActFeed"]
    assert [k.name for k in feed.children] == ["galIbActivity"]
    assert feed.props["LayoutOverflowY"] == "LayoutOverflow.Scroll"
    # Fra Tablet og op; paa en telefon er feeden saa hoej som sine linjer,
    # og fanen er den eneste scroll (issue #508).
    import mobile
    assert mobile.desk(feed.props["Height"]).startswith("Max(80, Parent.Height - (")
    # Indholdsfladen gaar helt ned til panelets bund - ikke kun saa hoej som
    # den laengste fane.
    h = c["conIbDetContent"].props["Height"]
    assert h.startswith(f"Max({P.DET_SAFE_MIN_H}, App.Height - ")
    assert "colIbActivity" not in h and "varIbTab" not in h
    # Kommentarfeltet og Internal note er de samme som foer.
    assert [k.name for k in c["conIbComposer"].children] == ["conIbCommentBox", "chkIbInternal",
                                                            "txtIbCommentHint"]


def test_yaml_uses_images_not_modern_icons_in_the_panel():
    y = open(SCREEN, encoding="utf-8").read()
    for n in ("imgIbDetApp", "imgIbFactReporter", "imgIbFactAssigned", "imgIbActWho",
              "imgIbDetDescIcon", "conIbActFeed"):
        assert y.count(f"- {n}:") == 1, n
    assert "- bdgIbActRole:" not in y
