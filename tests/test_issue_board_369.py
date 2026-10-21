# -*- coding: utf-8 -*-
"""Issue #369: sagens sidepanel har et klarere hierarki.

Status som maerke under titlen; Issue information (Application, Section,
Priority); Ticket details (Requester, Assigned to, Severity, Reported,
Updated); teksterne i Description-fanen i hver sin diskrete flade, hvis
hoejde foelger teksten, med en anelse stoerre skrift."""
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
    return {c.name: c for c in _walk(P.build_detail())}


def _under(ctrls, root):
    return {c.name for c in _walk(ctrls[root])}


def test_status_stands_alone_under_the_title():
    c = _ctrls()
    # Issue #475: handlingerne staar paa status-linjen, til hoejre.
    assert [k.name for k in c["conIbDetMeta"].children] == ["bdgIbDetStatus", "conIbDetActions"]
    top = [k.name for k in c["conIbDetTop"].children]
    assert top.index("conIbDetMeta") < top.index("conIbDetInfo") < top.index("conIbDetFacts")


def test_each_value_is_shown_once_in_its_section():
    c = _ctrls()
    info = _under(c, "conIbDetInfo")
    facts = _under(c, "conIbDetFacts")
    for n in ("txtIbDetApp", "txtIbDetSection", "bdgIbDetPriority"):
        assert n in info and n not in facts, n
    for n in ("txtIbFactReporter", "txtIbFactAssigned", "txtIbFactSeverity",
              "txtIbFactReported", "txtIbFactUpdated"):
        assert n in facts and n not in info, n
    # Issue #475: overskrifterne er ikke smaa versaler mere.
    assert c["txtIbDetInfoTitle"].props["Text"] == '"Issue information"'
    assert c["txtIbDetFactsTitle"].props["Text"] == '"Ticket details"'
    # Ingen gammel Application/Section-linje ved siden af status.
    for old in ("conIbDetWhere", "conIbDetBadges"):
        assert old not in c, old
    # Hver kilde vises een gang i hele panelet.
    texts = [k.props.get("Text", "") for k in c.values()]
    for field in ("varIbSel.Application", "varIbSel.Section"):
        assert texts.count(field) == 1, field


def test_text_blocks_are_compact_boxes_that_follow_the_text():
    import ib_parts as P
    import layout_tokens as lay
    c = _ctrls()
    for name in ("IbDetDesc", "IbDetSteps", "IbDetExpected", "IbDetActual"):
        block = c[f"con{name}"]
        # Issue #475: ikonet til venstre, overskriften og fladen ved siden af.
        assert [k.name for k in block.children] == [f"img{name}Icon", f"con{name}Body"]
        assert [k.name for k in c[f"con{name}Body"].children] == [f"txt{name}Label", f"con{name}Box"]
        box = c[f"con{name}Box"]
        assert box.props["BorderColor"] == P.C_CARD_BORDER
        assert box.props["RadiusTopLeft"] == "8"
        # Hoejden er regnet af teksten - ingen fast hoejde.
        assert "Len(t)" in box.props["Height"]
        body = c[f"txt{name}"]
        assert body.props["Wrap"] == "true"
        assert int(body.props["Size"]) == lay.SIZE_BODY + 1
    # Description-fanen er samme fane som foer.
    assert c["conIbDetDetails"].props["Visible"] == 'varIbTab = "details"'


def test_yaml_has_the_new_hierarchy():
    y = open(SCREEN, encoding="utf-8").read()
    pos = [y.index(f"- {n}:") for n in ("bdgIbDetStatus", "conIbDetActions", "conIbDetInfo",
                                       "conIbDetFacts", "conIbDetTabs", "conIbDetDescBox")]
    assert pos == sorted(pos)
    assert "- conIbDetWhere:" not in y
