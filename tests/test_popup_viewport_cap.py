# -*- coding: utf-8 -*-
"""Popups that can grow with their content are capped by App.Height, so the
header, Close and footer stay on screen on a small phone."""
import glob
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENS = sorted(glob.glob(os.path.join(ROOT, "BIO SAP App", "Screen*.pa.yaml")))
CAPPED = ("conEqPasteBody", "conMatPasteBody", "conMpPasteBody", "conFlPasteBody", "conVhpMatBody", "galVhpItemObjects",
          "inpVhpLongTextBox")


def _walk(node, out):
    for c in node.get("Children", []) or []:
        for n, v in c.items():
            out[n] = v
            _walk(v, out)


def test_growing_popup_parts_are_capped_by_app_height():
    found = {}
    for path in SCREENS:
        with open(path, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        for _, scr in doc["Screens"].items():
            _walk(scr, found)
    for name in CAPPED:
        assert name in found, name
        h = str((found[name].get("Properties") or {}).get("Height", ""))
        assert "App.Height" in h, f"{name}: Height = {h}"
