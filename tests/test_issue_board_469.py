# -*- coding: utf-8 -*-
"""Issue #469: kolonnen Activity i Issue Boards oversigt aabner sagen
direkte paa fanen Activity - samme moenster som papirclipsen, der aabner
Attachments. Taleboblen (Fluent "Comment") og tallet er EEN knap med een
hover-flade; resten af raekken aabner stadig Description."""
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


def test_activity_cell_is_one_button_that_opens_the_activity_tab():
    ctrls = _list()
    for suffix in ("", "C"):
        btn = ctrls[f"btnIbRowAct{suffix}"]
        # Issue #489: taleboblen med tallet indeni er eet klikbart billede
        # (tests/test_issue_board_489.py) - ikke den gamle ModernIcon.
        assert btn.control == "Image"
        assert "LookUp(colIbActN, TicketId = ThisItem.Id).N" in btn.props["Image"]
        # Samme aabning som papirclipsen - bare fanen Activity.
        assert btn.props["OnSelect"] == P.OPEN_ROW_ACT
        assert 'Set(varIbTab, "activity")' in btn.props["OnSelect"]
        assert btn.props["OnSelect"] == P.OPEN_ROW_FILES.replace(
            'Set(varIbTab, "files")', 'Set(varIbTab, "activity")').replace(P.LOAD_FILES + ";\n", "")
        assert btn.props["AccessibleLabel"] and btn.props["Tooltip"] == '"Show activity"'
        assert f"icoIbRowAct{suffix}" not in ctrls and f"txtIbRowAct{suffix}" not in ctrls
    # Resten af raekken aabner stadig Description.
    assert 'Set(varIbTab, "details")' in P.OPEN_ROW
    assert ctrls["btnIbRowOpen"].props["OnSelect"] == P.OPEN_ROW


def test_activity_button_lies_above_the_row_hit_area():
    text = open(SCREEN, encoding="utf-8").read()
    opener = text.index("- btnIbRowOpen:")
    assert opener < text.index("- btnIbRowAct:") and opener < text.index("- btnIbRowActC:")
    assert "- icoIbRowAct" not in text and "- txtIbRowAct" not in text
