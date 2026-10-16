# -*- coding: utf-8 -*-
"""Issue #301: Issue Boardets vaerktoejslinje er kompakt og venstrestillet.

Ingen kontrol straekkes for at fylde kortet: sorteringen staar kort efter
kontakterne, soegefeltet har en moderat bredde, og listerne staar lige
efter det. Den ubrugte plads bliver til hoejre."""
import os
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Issue Board", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def _eval(expr, app_w):
    import check_layout as cl
    return cl.evaluate(expr, app_w, 3, 3, 3)


def test_nothing_in_the_toolbar_grows():
    import ib_parts as P
    top, filters = P.build_filters()
    for row in (top, filters):
        for c in row.children:
            assert c._grow is None, c.name
            assert c.props.get("FillPortions", "0") == "0", c.name
    # Soegefeltet vokser kun inden i sin egen (faste) gruppe.
    search_row = filters.children[0]
    assert search_row.children[0].name == "inpIbSearch"


def test_sort_sits_shortly_after_the_switches():
    import ib_parts as P
    top, _f = P.build_filters()
    gap = top.children[2]
    assert gap.name == "rctIbTbSortGap"
    for w in (1280, 1600, 1920):
        assert _eval(gap.props["Width"], w) == P.SORT_GAP
    # Paa en smal Desktop giver luften efter, saa linjen stadig staar vandret.
    assert 0 <= _eval(gap.props["Width"], 1024) <= P.SORT_GAP
    assert _eval(P.TOP_OK, 1024) not in (0, False)


def test_search_has_a_moderate_width_and_leaves_space_right():
    import ib_parts as P
    _t, filters = P.build_filters()
    search_row, pair_a, pair_b = filters.children
    for w in (1280, 1600, 1920, 2560):
        tb = _eval(P.TB_W, w)
        sw = _eval(search_row.props["Width"], w)
        assert sw == P.SEARCH_W
        used = sw + _eval(pair_a.props["Width"], w) + _eval(pair_b.props["Width"], w) + 2 * P.TB_GAP
        assert used <= tb
    # Bred skaerm: tydeligt ubrugt plads til hoejre.
    assert _eval(P.TB_W, 1920) - P.FLT_ROOMY_NEED > 600
    # Smal Desktop: soegefeltet giver efter, men aldrig under mindstebredden,
    # og linjen staar stadig vandret.
    sw = _eval(search_row.props["Width"], 1024)
    # (2 px slaek som i formlen.)
    assert P.SEARCH_MIN - 2 <= sw <= P.SEARCH_W
    assert _eval(P.FLT_OK, 1024) not in (0, False)


def test_lists_are_wide_enough_for_typical_values_when_there_is_room():
    import ib_parts as P
    _t, filters = P.build_filters()
    app, sec = filters.children[1].children
    status, pri = filters.children[2].children
    assert _eval(app.props["Width"], 1600) >= P._dd_w("Functional Location")
    assert _eval(sec.props["Width"], 1600) >= P._dd_w("Issue list and filters")
    assert _eval(status.props["Width"], 1600) >= P._dd_w("Ready for retest")
    # Ens afstand: 8 px inden i parrene og mellem grupperne.
    assert filters.props["LayoutGap"] == str(P.TB_GAP) == "8"
    assert filters.children[1].props["LayoutGap"] == "8"


def test_mobile_still_stacks():
    import ib_parts as P
    for ok in (P.TOP_OK, P.FLT_OK, P.FLT_ROOMY):
        assert _eval(ok, 420) in (0, False)
