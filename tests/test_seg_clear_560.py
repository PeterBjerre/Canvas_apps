# -*- coding: utf-8 -*-
"""Issue #560: ja/nej-skinnerne i sidepanelerne (tydeligst Strategic part og
Wear part i Materials) blev STADIG klippet forneden efter #550.

#550 gjorde skinnen 2 px hoejere, men cellen voksede lige saa meget, saa
skinnens bundkant laa stadig paa den sidste pixel af cellen - og cellen,
raekken og gitteret skjuler alle deres overloeb. En container tegner sin
kant paa yderkanten (samme erfaring som #150, #492 og #503), saa kanten og
de runde hjoerner blev skaaret af. #550's test maalte kun skinnen indvendig,
aldrig skinnen mod sin forælder - derfor fangede den det ikke.

Nu skal foraelderen give hver skinne build_helpers.SEG_CLEAR px luft under
sig. Testen laeser de genererede skaerme og maaler skinnen mod foraelderen
paa telefon, tablet og desktop."""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_helpers as bh  # noqa: E402
import gen_screen  # noqa: E402
import mobile  # noqa: E402

APP = os.path.join(ROOT, "BIO SAP App")
RANKS = (1, 2, 3)          # telefon, tablet, desktop
# Sidepanelernes ja/nej-celler - de skal maales (ikke springes over).
MUST = {"conMatStrategicPart", "conMatWearPart", "conMatIsStockItem",
        "conMatReplacesExisting", "conMpExistsInSap"}


def _p(body, key, default="0"):
    return str((body.get("Properties") or {}).get(key, default)).strip().lstrip("=").strip()


def _eval(expr, rank):
    """Et tal-udtryk med If/Max/Min og LayoutRank - None, hvis det afhaenger
    af andet (fx App.Width eller en variabel)."""
    rest = re.sub(r"\b(If|Max|Min|LayoutRank|LayoutDirection\.(Vertical|Horizontal))\b", "", expr)
    if re.search(r"[A-Za-z_']", rest):
        return None
    env = {"If": lambda c, a, b: a if c else b, "Max": max, "Min": min, "LayoutRank": rank}
    return eval(expr, {"__builtins__": {}}, env)  # noqa: S307 - genereret YAML, kun tal


def _direction(body, rank):
    d = _p(body, "LayoutDirection", "LayoutDirection.Vertical")
    m = re.fullmatch(r"If\(LayoutRank < 2, LayoutDirection\.(\w+), LayoutDirection\.(\w+)\)", d)
    if m:
        return m.group(1) if rank < 2 else m.group(2)
    return d.split(".")[-1]


def _parents():
    """(foraelder-navn, foraelder, skinnens indeks, boern) for hver skinne."""
    def walk(items):
        for it in items or []:
            (n, b), = it.items()
            kids = [list(c.items())[0] for c in b.get("Children") or []]
            for i, (_kn, kb) in enumerate(kids):
                if _p(kb, "Fill", "") == "C.'seg-track-bg'":
                    yield n, b, i, kids
            yield from walk(b.get("Children"))
    for f in glob.glob(os.path.join(APP, "Screen*.pa.yaml")):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        for s in d["Screens"].values():
            yield from walk(s.get("Children"))


def test_clear_token():
    assert bh.SEG_CLEAR >= 2 * bh.SEG_BORDER


def test_footprint_counts_clear():
    """group(clear=...) roerer ikke containerens egen hoejde, men
    foraelderens regnskab (gen_screen og mobile.restack) giver den luften."""
    a = bh.text_ctrl("txtT560", '"x"', height=20)
    seg = bh.segmented("conT560Seg", [("No", "No", "true", "false", None),
                                      ("Yes", "Yes", "false", "false", None)])
    assert seg.clear == bh.SEG_CLEAR
    cell = bh.group("conT560", [a, seg], gap=6)
    lbl = a.h
    desk = _eval(cell.props["Height"], 3)
    assert desk == lbl + 6 + bh.SEG_TRACK_H + bh.SEG_CLEAR, cell.props["Height"]
    assert _eval(seg.props["Height"], 3) == bh.SEG_TRACK_H
    assert mobile.restack(cell) == lbl + 6 + bh.SEG_TRACK_H_MOBILE + bh.SEG_CLEAR
    row = bh.group("conT560Row", [seg], direction="Horizontal")
    assert _eval(row.props["Height"], 3) == bh.SEG_TRACK_H + bh.SEG_CLEAR
    assert gen_screen.footprint(a) == lbl


def test_every_track_has_clearance_in_its_parent():
    measured = set()
    for pname, parent, idx, kids in _parents():
        for r in RANKS:
            ph = _eval(_p(parent, "Height"), r)
            if ph is None:
                continue          # haenger af bredde/variabler - maales ikke her
            vis = [_p(kb, "Visible", "true") for _kn, kb in kids]
            if any(v != "true" for v in vis):
                continue
            hs = [_eval(_p(kb, "Height"), r) for _kn, kb in kids]
            if None in hs:
                continue
            pt, pb = _eval(_p(parent, "PaddingTop"), r), _eval(_p(parent, "PaddingBottom"), r)
            bt = _eval(_p(parent, "BorderThickness"), r) if _p(parent, "BorderColor", "") else 0
            gap = _eval(_p(parent, "LayoutGap"), r)
            track_h = hs[idx]
            if _direction(parent, r) == "Vertical":
                if idx != len(kids) - 1:
                    continue      # skinnen staar ikke nederst
                used = sum(hs) + gap * (len(hs) - 1)
            else:
                used = track_h
            room = ph - pt - pb - 2 * bt - used
            assert room >= bh.SEG_CLEAR, (pname, kids[idx][0], r, ph, used, room)
            measured.add(pname)
    assert MUST <= measured, MUST - measured
