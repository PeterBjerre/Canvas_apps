# -*- coding: utf-8 -*-
"""Issue #550: segmenterne i sidepanelerne (ja/nej og Details / Objects /
Documents) blev klippet forneden. Skinnen (build_helpers.seg_track) har en
kant paa 1 px, der tager plads inde i containeren, men hoejden var kun
polstring + knap. Nu regnes kanten med - eet sted, for alle skinner.

Testen laeser de genererede skaerme: hver skinne (Fill = seg-track-bg) skal
paa telefon, tablet og desktop vaere mindst kant + polstring + det hoejeste
segment hoej, og - hvor bredden er et tal - bred nok til segmenterne."""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_helpers as bh  # noqa: E402

APP = os.path.join(ROOT, "BIO SAP App")
RANKS = (1, 2, 3)          # telefon, tablet, desktop
# Sidepanelernes skinner, som issuet naevner - de skal findes.
MUST = {"conMatEditorTabs", "conMatIsStockItemSeg", "conMatStrategicPartSeg",
        "conMatWearPartSeg", "conEqEditorTabs", "conMpExistsInSapSeg"}


def _walk(items):
    for it in items or []:
        (n, b), = it.items()
        yield n, b
        yield from _walk(b.get("Children"))


def _p(body, key, default="0"):
    return str((body.get("Properties") or {}).get(key, default)).strip().lstrip("=").strip()


def _eval(expr, rank):
    """Et simpelt tal-udtryk med If/Max/Min og LayoutRank - None, hvis det
    afhaenger af andet (fx App.Width)."""
    if re.search(r"[A-Za-z_.']", re.sub(r"\b(If|Max|Min|LayoutRank)\b", "", expr)):
        return None
    env = {"If": lambda c, a, b: a if c else b, "Max": max, "Min": min, "LayoutRank": rank}
    return eval(expr, {"__builtins__": {}}, env)  # noqa: S307 - genereret YAML, kun tal


def _tracks():
    for f in glob.glob(os.path.join(APP, "Screen*.pa.yaml")):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        for s in d["Screens"].values():
            for n, b in _walk(s.get("Children")):
                if _p(b, "Fill", "") == "C.'seg-track-bg'":
                    yield n, b


def test_tokens():
    assert bh.SEG_TRACK_H == bh.SEG_BTN_H + 2 * (bh.SEG_PAD + bh.SEG_BORDER)
    assert bh.SEG_TRACK_H_MOBILE == bh.SEG_BTN_H_MOBILE + 2 * (bh.SEG_PAD + bh.SEG_BORDER)
    assert bh.segmented_width(2) == 2 * bh.seg_button_width() + bh.SEG_GAP + 2 * bh.SEG_EDGE


def test_every_track_fits_its_segments_with_border():
    seen = set()
    for name, body in _tracks():
        seen.add(name)
        kids = [list(c.values())[0] for c in body.get("Children") or []]
        assert kids, name
        for r in RANKS:
            h = _eval(_p(body, "Height"), r)
            assert h is not None, (name, _p(body, "Height"))
            bt = _eval(_p(body, "BorderThickness"), r)
            pt, pb = _eval(_p(body, "PaddingTop"), r), _eval(_p(body, "PaddingBottom"), r)
            tallest = max(_eval(_p(k, "Height"), r) for k in kids)
            assert h >= 2 * bt + pt + pb + tallest, (name, r, h, bt, pt, pb, tallest)
            w = _eval(_p(body, "Width"), r)
            ws = [_eval(_p(k, "Width"), r) for k in kids]
            if w is None or None in ws:
                continue
            gap = _eval(_p(body, "LayoutGap"), r)
            pl, pr = _eval(_p(body, "PaddingLeft"), r), _eval(_p(body, "PaddingRight"), r)
            need = sum(ws) + gap * (len(ws) - 1) + pl + pr + 2 * bt
            assert w >= need, (name, r, w, need)
    assert MUST <= seen, MUST - seen
