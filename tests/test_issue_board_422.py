# -*- coding: utf-8 -*-
"""Issue #422: vedhaeftninger og Activity i Issue Boards oversigt.

Papirclipsen staar kun, naar sagen HAR filer (kolonnen FileCount, hentet
med oversigten - issue #443; foer connectorens 'Has attachments'). En ny kolonne ACTIVITY viser
antallet af haendelser pr. sag - fra EEN hentning af IB_TicketComments
(kun TicketId) og en optaelling i hukommelsen, ikke et kald pr. raekke.
Tallet foelger med, naar en kommentar sendes, og naar sagen aabnes."""
import os
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Issue Board", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import ib_config as cfg  # noqa: E402
import ib_parts as P  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml")


def _walk(ctrls):
    for c in ctrls:
        yield c
        yield from _walk(getattr(c, "children", []) or [])


def _list():
    return {c.name: c for c in _walk([P.build_list()])}


def test_paperclip_only_when_the_issue_has_files():
    ctrls = _list()
    for name in ("btnIbRowAttach", "btnIbRowAttachC"):
        b = ctrls[name]
        # Issue #443: raekkens eget tal - FileCount (tests/test_issue_board_442_443.py).
        assert b.props["Visible"].endswith("&& Coalesce(ThisItem.FileCount, 0) > 0")
        # Et tegn paa filer, der aabner fanen Attachments - ikke en upload-knap.
        assert "Add screenshots" not in b.props["AccessibleLabel"]
        assert 'Set(varIbTab, "files")' in b.props["OnSelect"]
    # Feltet hentes med oversigten (samme $select) - intet opslag pr. sag.
    assert "FileCount: r.FileCount" in P.FETCH_ALL
    assert "FileCount" in P.ROW
    # De hentede filer retter tegnet - ogsaa efter Save paa fanen.
    assert "UpdateIf(colIbAll, Id = varIbSelId, { FileCount: fileN })" in P.LOAD_FILES
    assert "Patch(varIbSel, { FileCount: fileN })" in P.LOAD_FILES


def test_activity_counts_are_one_query_not_one_per_row():
    # Een hentning af kommentarlisten, kun TicketId, samtidig med sagerne.
    fetch = f"ShowColumns(Sort({cfg.L_COMMENTS}, ID, SortOrder.Descending), TicketId)"
    assert fetch in P.FETCH_ACT_N
    concurrent = P.LOAD.split("Concurrent(")[1].split("\n    );")[0]
    assert P.FETCH_ACT_N in concurrent and "colIbAll" in concurrent
    assert P.LOAD.index(P.COUNT_ACT_N) > P.LOAD.index(P.FETCH_ACT_N)
    assert P.FETCH_ACT_N in P.SYNC and P.COUNT_ACT_N in P.SYNC
    assert "GroupBy(colIbActRaw, TicketId, Grp)" in P.COUNT_ACT_N
    # Raekken slaar op i hukommelsen - aldrig i SharePoint-listen.
    ctrls = _list()
    for suffix in ("", "C"):
        # Issue #469: ikon og tal er een knap (tests/test_issue_board_469.py).
        btn = ctrls[f"btnIbRowAct{suffix}"]
        assert "colIbActN" in btn.props["Image"] and cfg.L_COMMENTS not in btn.props["Image"]
        # Kun for rapportoeren og admins (som fanen Activity).
        assert btn.props["Visible"] == P.ROW_SEE_ACT
        assert "ThisItem.Reporter = varIbMe" in P.ROW_SEE_ACT
        # 0 er dempet (issue #489: en streg-boble - tests/test_issue_board_489.py).
        assert "If(n = 0," in btn.props["Image"]
    # Cellen selv skjules aldrig - ellers flytter kolonnerne sig.
    assert "Visible" not in ctrls["conIbRowAct"].props
    text = open(SCREEN, encoding="utf-8").read()
    assert f"CountRows(Filter({cfg.L_COMMENTS}" not in text
    assert "ACTIVITY" in text and '"FILES"' in text


def test_counts_follow_a_posted_comment_and_an_opened_issue():
    # Efter Post comment: een mere paa den sag, kommentaren hoerer til.
    assert P.POST_ACT_N in P.POST
    assert "TicketId = varIbPostFor" in P.POST_ACT_N and "+ 1" in P.POST_ACT_N
    ok = P.POST.index('varIbPostRes.ok = "yes"')
    failed = P.POST.index('Set(varIbPostStage, "failed")')
    assert ok < P.POST.index(P.POST_ACT_N) < failed
    # Naar sagens Activity hentes, er den facit (samme tal som fanen).
    assert P.SET_ACT_N in P.LOAD_ACTIVITY
    assert 'CountRows(Filter(colIbActivity, Kind <> "Reported"))' in P.SET_ACT_N
    names = [n for n, _s in P.collections()]
    assert "colIbActN" in names and "colIbActRaw" in names


def test_columns_still_fit_the_smallest_desktop():
    assert P._fixed(False) <= 806
    keys = [c[0] for c in P.LIST_COLS]
    assert keys[-2:] == ["ACTV", "ACT"]
