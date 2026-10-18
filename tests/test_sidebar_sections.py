# -*- coding: utf-8 -*-
"""
Issue #368: sidebaren har afsnit.

  - Masterdata Hub staar alene oeverst, uden overskrift.
  - MASTER DATA: Functional Location, Maintenance Plan, Materials,
    Equipments, Measuring Points. REFERENCE: KKS lookup.
    ISSUES & TESTING: Issue Board.
  - I det aabne panel er overskriften en tekst (ikke klikbar) i versaler
    og daempet farve; i den lukkede skinne en tynd streg.
  - Paa alle skaerme det samme.

Testene laeser de GENEREREDE skaerme.

    python3 -m pytest tests/test_sidebar_sections.py
"""
import glob
import os
import re

from conftest import ROOT

APP_DIR = os.path.join(ROOT, "BIO SAP App")
SCREENS = sorted(glob.glob(os.path.join(APP_DIR, "Screen*.pa.yaml")))
HUB = os.path.join(APP_DIR, "ScreenMdHub.pa.yaml")

WANT = [
    "Hub",
    "MASTER DATA", "Functionallocation", "Vhplan", "Material", "Equipment", "Measuringpoint",
    "REFERENCE", "Kks",
    "ISSUES & TESTING", "Issueboard",
]
SLUG = {"MasterData": "MASTER DATA", "Reference": "REFERENCE",
        "IssuesTesting": "ISSUES & TESTING"}
FIXED = {"Brand", "Toggle", "Message", "Lang", "Menu", "Page", "Scrim", "Help", "Theme"}
ROW = re.compile(r"^\s*- (?:img[A-Z][a-z]+Nav([A-Z][a-z]+)(Open)?"
                 r"|con[A-Z][a-z]+NavSec([A-Za-z]+?)(Open)?):\s*$", re.M)


def _rows(path):
    """{'': [...], 'Open': [...]}: punkter og afsnit i YAML-orden."""
    out = {"": [], "Open": []}
    for item, iopen, sec, sopen in ROW.findall(open(path, encoding="utf-8").read()):
        if item and item not in FIXED:
            out[iopen].append(item)
        elif sec and not sec.startswith("Rule"):
            out[sopen].append(SLUG[sec])
    return out


def test_hub_order_and_sections():
    got = _rows(HUB)
    assert got["Open"] == WANT
    assert got[""] == WANT


def test_same_sections_on_every_screen():
    want = _rows(HUB)
    for path in SCREENS:
        assert _rows(path) == want, os.path.basename(path)


def _blocks(text, pattern):
    """Kontrollernes YAML-blokke (navn -> tekst) for navne, der matcher."""
    lines = text.split("\n")
    out = {}
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)- (%s):\s*$" % pattern, line)
        if not m:
            continue
        ind = len(m.group(1))
        body = []
        for nxt in lines[i + 1:]:
            if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= ind:
                break
            body.append(nxt)
        out[m.group(2)] = "\n".join(body)
    return out


def test_open_header_is_muted_uppercase_label():
    for path in SCREENS:
        blocks = _blocks(open(path, encoding="utf-8").read(), r"txt\w+NavSec\w+")
        texts = []
        for name, block in blocks.items():
            assert "Control: ModernText" in block, name
            assert "OnSelect" not in block, name
            assert "=C.'text-muted'" in block, name
            assert "=T.micro" in block, name
            texts.append(re.search(r'Text: \|-\n\s+="(.*)"', block).group(1))
        # Kun i panelet - tre overskrifter pr. skaerm.
        assert sorted(texts) == sorted(SLUG.values()), os.path.basename(path)


def test_rail_uses_thin_divider_not_text():
    for path in SCREENS:
        blocks = _blocks(open(path, encoding="utf-8").read(), r"con\w+NavSecRule\w+")
        assert len(blocks) == 3, os.path.basename(path)
        for name, block in blocks.items():
            assert re.search(r"Fill: \|-\n\s+=C.'border-subtle'", block), name
            assert re.search(r"Height: \|-\n\s+=1\n", block), name
            assert "OnSelect" not in block, name


def test_rail_uses_thin_divider_not_text():
    for path in SCREENS:
        text = open(path, encoding="utf-8").read()
        rules = re.findall(r"- con\w+NavSecRule\w+:\n(?:.*\n){0,12}?\s+Fill: \|-\n\s+=(.*)\n"
                           r"(?:.*\n){0,4}?\s+Height: \|-\n\s+=(\d+)\n", text)
        assert len(rules) == 3, (os.path.basename(path), rules)
        assert all(f == "C.'border-subtle'" and h == "1" for f, h in rules)
        # Overskriftsteksten staar kun i panelet - tre i alt pr. skaerm.
        assert len(re.findall(r"- txt\w+NavSec\w+:", text)) == 3


def test_sections_follow_nav_order():
    import sys
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import env_config as env
    assert "hub" not in env.NAV_SECTION
    secs = [env.NAV_SECTION[k] for k in env.NAV_ORDER if k != "hub"]
    # Hvert afsnit staar samlet.
    runs = [s for i, s in enumerate(secs) if i == 0 or secs[i - 1] != s]
    assert runs == ["Master data", "Reference", "Issues & testing"]
