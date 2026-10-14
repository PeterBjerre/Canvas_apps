# -*- coding: utf-8 -*-
"""Hubben (UX-review 2026-10, M3): kompakte fliser med New, "Continue where
you left off" og sorterbare kolonner."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "Masterdata Hub", "build")
if HUB not in sys.path:
    sys.path.insert(0, HUB)

import build_hub as bh  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMdHub.pa.yaml")


def _yaml():
    return open(SCREEN, encoding="utf-8").read()


def _block(y, name, n=3000):
    i = y.index(f"- {name}:")
    return y[i:i + n]


def test_tiles_are_72_px_with_a_new_icon_button():
    assert bh.TILE_H == 76
    y = _yaml()
    for d in bh.DOMAINS:
        b = _block(y, f"imgMdTileNew{d['short']}")
        assert "Control: Image" in b
        assert f'"New {d["name"].lower()} request"' in b


def test_continue_where_you_left_off_opens_the_latest_draft_in_edit():
    assert "Status.Value = \"Kladde\"" in bh.RESUME_REFRESH
    assert "SortOrder.Descending" in bh.RESUME_REFRESH
    assert bh.RESUME_REFRESH in bh.HUB_ON_VISIBLE
    go = _block(_yaml(), "btnMdResumeGo", 4000)
    assert '"edit:" & varMdResume.RequestGuid' in go
    assert "ThisItem" not in go


def test_every_sort_branch_names_its_column_as_a_constant():
    assert bh.SORT_COLS["REQUEST"] == "Title"
    assert bh.COL_NO == "RequestNo"
    for key, col in bh.SORT_COLS.items():
        assert f'"{col}", {bh.SORT_ORDER}' in bh.ITEMS, key
    # Filteret staar i hver gren - ellers ville With/variabler bryde
    # delegeringen.
    assert bh.ITEMS.count("SortByColumns(") == len(bh.SORT_COLS)
    assert bh.ITEMS.count(bh._FILTERED.strip()) == len(bh.SORT_COLS)
    assert "varMdSort" in bh.ITEMS


def test_sortable_headers_are_buttons_and_the_rest_stay_text():
    y = _yaml()
    for i, (t, _w) in enumerate(bh.COLS):
        if t in bh.SORT_COLS:
            assert f"- btnMdH{i}:" in y, t
        else:
            assert f"- txtMdH{i}:" in y, t
