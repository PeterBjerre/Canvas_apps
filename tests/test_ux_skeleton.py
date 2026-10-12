# -*- coding: utf-8 -*-
"""Pladsholder-raekker mens en liste hentes (UX-review 2026-10, M7)."""
import os

import build_helpers as bh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "BIO SAP App")


def _yaml(screen):
    return open(os.path.join(APP, screen), encoding="utf-8").read()


def test_skeleton_rows_are_containers_with_one_spoken_text():
    g = bh.skeleton_rows("conXSkeleton", "varXLoading", rows=3, label="Loading x...")
    assert g.props["Visible"] == "varXLoading"
    say, *rows = g.children
    assert say.name == "txtXSkeletonSay" and '"Loading x..."' in say.props["Text"]
    assert len(rows) == 3
    for r in rows:
        # Kun containere: ingen tab-stop og ingen etiket at kraeve (regel 37/38).
        assert all("Container" in b.control for b in r.children), r.name


def test_issue_board_shows_skeleton_rows_not_a_full_screen_spinner():
    y = _yaml("ScreenIssueBoard.pa.yaml")
    assert "conIbSkeleton:" in y
    assert "imgIbLoading:" not in y
    # Den tomme tilstand siger ikke "ingen sager", mens der hentes.
    i = y.index("- conIbEmpty:")
    assert "!varIbLoading" in y[i:i + 4000]


def test_the_hub_marks_its_load_and_shows_skeleton_rows():
    y = _yaml("ScreenMdHub.pa.yaml")
    assert "conMdSkeleton:" in y
    assert "Set(varMdLoading, true)" in y and "Set(varMdLoading, false)" in y
    i = y.index("- conMdEmpty:")
    assert "!varMdLoading" in y[i:i + 4000]
