# -*- coding: utf-8 -*-
"""Hubben (UX-review 2026-10, M3): kompakte fliser med New og sorterbare
kolonner. ("Continue where you left off" er fjernet igen, issue #273.)"""
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


def test_continue_where_you_left_off_is_gone():
    """Issue #273: sektionen er fjernet helt - UI, hentning og variabel.
    Filtrene ligger lige under fliserne (kun banneren om returnerede
    anmodninger, naar den vises, kan staa imellem)."""
    for name in ("RESUME_REFRESH", "RESUME_N", "build_resume"):
        assert not hasattr(bh, name), name
    assert "varMdResumeList" not in bh.HUB_ON_VISIBLE
    y = _yaml()
    for bad in ("MdResume", "varMdResumeList", "Continue where you left off",
                "Your latest drafts and requests that need information"):
        assert bad not in y, bad
    body = y[y.index("- conMdBody:"):]
    order = [body.index(f"- {n}:") for n in ("conMdTiles", "conMdRetBanner", "conMdFlt", "conMdListCard")]
    assert order == sorted(order)


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
