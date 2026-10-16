# -*- coding: utf-8 -*-
"""Issue #291: Issue Boardets vaerktoejslinje paa to raekker.

Linje 1: kontakterne (scope og tilstand) og sorteringen (issue #301: kort
efter kontakterne, ikke yderst til hoejre).
Linje 2: soegefeltet, Application, Section, Status og Priority.
Kun een taeller under filtrene - admin-statistiklinjen er vaek."""
import os
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Issue Board", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml")


def _names(ctrls):
    return [c.name for c in ctrls]


def test_toolbar_rows_have_the_requested_order():
    import ib_parts as P
    top, filters = P.build_filters()
    assert _names(top.children) == ["conIbScope", "conIbState", "rctIbTbSortGap", "drpIbSort"]
    assert _names(filters.children) == ["conIbSearchRow", "conIbFltPairA", "conIbFltPairB"]
    pairs = [c for p in filters.children[1:] for c in p.children]
    assert _names(pairs) == ["drpIbFltApp", "drpIbFltSection", "drpIbFltStatus", "drpIbFltPriority"]
    # Section er altid synlig (kun laast, til en Application er valgt).
    assert "Visible" not in pairs[1].props
    # Sorteringen skilles fra kontakterne af en fast luft - kun naar linjen
    # staar vandret (issue #301: intet fyld, der skubber den til hoejre).
    gap = top.children[2]
    assert gap._grow is None and gap.props["Visible"] == P.TOP_OK


def test_both_rows_fit_on_one_line_from_desktop():
    import check_layout as cl
    import ib_parts as P
    for ok in (P.TOP_OK, P.FLT_OK):
        assert cl.evaluate(ok, 1024, 3, 3, 3) not in (0, False)
        assert cl.evaluate(ok, 420, 3, 3, 3) in (0, False)


def test_switches_are_compact():
    import ib_parts as P
    from build_helpers import fit_button_width, ICON_W, SEG_SIZE
    for t in ("All issues", "My issues", "Assigned to me", "Open", "Closed", "Archived"):
        old = fit_button_width('"%s"' % t, size=SEG_SIZE, min_w=0) + ICON_W + 8
        assert P._seg_w(t) < old
        # Plads til teksten, polstringen og fluebenet ved det valgte.
        assert P._seg_w(t) >= fit_button_width('"%s"' % t, size=SEG_SIZE, min_w=0) + 14


def test_only_one_result_count():
    text = open(SCREEN, encoding="utf-8").read()
    assert "txtIbAdminCounts" not in text
    assert " unassigned  ·  " not in text and " assigned to you  ·  " not in text
    assert "conIbSearchRow" in text
    import ib_parts as P
    card = P.build_list()
    names = _names(card.children)
    assert names[:3] == ["conIbTbTop", "conIbTbFilters", "conIbCountRow"]
    count = card.children[2].children[0]
    assert count.name == "txtIbCount"
    assert count.props["Text"] == ('With({ n: galIbList.AllItemsCount }, '
                                   'n & If(n = 1, " issue", " issues"))')
