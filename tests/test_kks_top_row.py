# -*- coding: utf-8 -*-
"""KKS-opslagets oeverste raekke: Function / Aggregate / Component (issue #345).

Efter #295 stod de tre faner i en flow_row (conKksKeys) inde i en anden
flow_row (conKksTopRow) - begge med retning og justering som formel. Det er
den konstruktion, der ogsaa gjorde Issue Boards vaerktoejslinje (#244) og
topbjaelken tomme i den udgivne app: Studio tegner de indlejrede knapper for
lavt, og LayoutOverflow.Hide skjuler dem. Nu staar fanerne direkte i een
fast, vandret raekke direkte i kortet."""
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenKks.pa.yaml")

import check_layout as cl  # noqa: E402
import layout_tokens as lay  # noqa: E402

KEYS = ("btnKksKeyFunction", "btnKksKeyAggregate", "btnKksKeyComponent")


def _find(items, name):
    for it in items or []:
        (n, b), = it.items()
        if n == name:
            return b
        hit = _find(b.get("Children"), name)
        if hit is not None:
            return hit
    return None


def _screen():
    d = yaml.safe_load(open(SCREEN, encoding="utf-8"))
    return d["Screens"]["ScreenKks"]["Children"]


def _kids(body):
    return [list(k.items())[0] for k in body.get("Children") or []]


def _ev(expr, w):
    return cl.evaluate(expr, w, 3, 4, 4)


def test_tabs_sit_directly_in_a_fixed_row_in_the_card():
    card = _find(_screen(), "conKksBrowseCard")
    kids = _kids(card)
    assert [n for n, _b in kids][:2] == ["conKksTopRow", "btnKksFlOpenNarrow"]
    row = dict(kids)["conKksTopRow"]
    p = row["Properties"]
    # Fast retning og justering - ingen formel, der kan skifte.
    assert p["LayoutDirection"].strip() == "=LayoutDirection.Horizontal"
    assert p["LayoutAlignItems"].strip() == "=LayoutAlignItems.Center"
    # 44 paa en telefon (issue #508), ellers som foer.
    assert p["Height"].strip() == "=If(LayoutRank < 2, 44, 32)"
    names = [n for n, _b in _kids(row)]
    assert names == list(KEYS) + ["conKksTopGap", "btnKksFlOpen"]
    # Ingen container med knapper i inde i raekken (den gamle conKksKeys).
    assert _find(_screen(), "conKksKeys") is None
    gap = dict(_kids(row))["conKksTopGap"]
    assert not gap.get("Children")


def test_tabs_keep_their_function_and_selected_state():
    row = _find(_screen(), "conKksTopRow")
    for name, key in zip(KEYS, ("function", "aggregate", "component")):
        p = dict(_kids(row))[name]["Properties"]
        assert p["OnSelect"].strip().startswith(f'=Set(varKksKey, "{key}");')
        # Issue #478: soegeteksten bliver staaende og gaelder i den nye type.
        assert "Reset(inpKksFind)" not in p["OnSelect"]
        # Det faelles segment-udtryk (issue #526): Outline, valgt = lyseblaa kant.
        assert p["Appearance"].strip() == "=ButtonAppearance.Outline"
        assert p["BorderColor"].strip() == (f'=If(varKksKey = "{key}", '
                                            "C.'seg-on-border', C.'border-default')")
        assert "Visible" not in p
        assert p["Height"].strip() == "=If(LayoutRank < 2, 44, 32)"   # issue #508
        assert p["LayoutMinWidth"] == p["Width"]


def test_row_fits_at_every_width_and_exactly_one_fl_button_shows():
    """Ved hver testbredde: fanerne (+ FL-knappen, naar den staar i raekken)
    kan staa i kortets indre bredde (en nedre graense), og praecis een af de
    to FL-knapper ses."""
    row = _find(_screen(), "conKksTopRow")
    narrow = _find(_screen(), "btnKksFlOpenNarrow")["Properties"]
    kids = dict(_kids(row))
    for w in cl.WIDTHS:
        # Paa en telefon er rammen og kortet smallere polstret (issue #508).
        phone = lay.rank_for(w) < lay.MOBILE_RANK
        card_w = (w - (56 if lay.rank_for(w) >= 2 else 0)
                  - (lay.SHELL_INSET_MOBILE if phone else 64) - (24 if phone else 36))
        need = 0.0
        shown = []
        for name, body in kids.items():
            p = body["Properties"]
            vis = _ev(p.get("Visible", "=true"), w)
            if vis is not None and not vis:
                continue
            shown.append(name)
            # Mellemrummet tager resten (Max(0, ...)) - kun dets afstand taeller.
            kw = 0 if name == "conKksTopGap" else _ev(p["Width"], w)
            need += kw + (8 if len(shown) > 1 else 0)
        assert need <= card_w + 0.5, (w, need, card_w)
        assert all(k in shown for k in KEYS), w
        wide = "btnKksFlOpen" in shown
        assert wide != bool(_ev(narrow["Visible"], w)), w
        if lay.rank_for(w) < 2:
            assert not wide, w
