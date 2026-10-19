# -*- coding: utf-8 -*-
"""Det graa sloer i Materials, Equipment og Measuring Point (issue #393).

Materials Documents-fane i sidepanelet satte varMatDocsId. Et sloer
(conMatBackdrop), der kun var bygget til dokumentPOPUPPEN, hang paa samme
variabel - men Materials har ingen popup, saa sloeret laa graat over
listen, og intet nulstillede variablen, naar panelet blev lukket.

Her tjekkes:
- et sloer, der hænger paa <X>DocsId, findes kun, hvor der ER en popup,
  og ligger da OVER sidepanelet (ellers lukker et klik paa den panelet);
- dokumentrudens raekke glemmes, naar panelet lukkes (X, Cancel, klik
  udenfor, OnHidden) og naar der skiftes raekke (forrige/naeste)."""
import os

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "BIO SAP App")
# (skaerm, tag, har dokumenter)
SCREENS = [("ScreenMaterial", "Mat", True), ("ScreenEquipment", "Eq", True),
           ("ScreenMeasuringPoint", "Mp", False)]


def _load(screen):
    with open(os.path.join(APP, screen + ".pa.yaml"), encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return next(iter(doc["Screens"].values()))


def _top(scr):
    return [(n, v) for c in scr["Children"] for n, v in c.items()]


def _prop(node, key):
    return str((node.get("Properties") or {}).get(key, "")).strip().lstrip("=").strip()


def _find(node, name):
    for c in node.get("Children", []) or []:
        for n, v in c.items():
            if n == name:
                return v
            hit = _find(v, name)
            if hit is not None:
                return hit
    return None


@pytest.mark.parametrize("screen,tag,docs", SCREENS)
def test_no_orphan_docs_scrim(screen, tag, docs):
    scr = _load(screen)
    top = _top(scr)
    names = [n for n, _v in top]
    scrims = [n for n, v in top if f"var{tag}DocsId" in _prop(v, "Visible")
              and n.endswith("Backdrop")]
    if f"con{tag}AttModal" not in names:
        assert scrims == [], f"{screen}: sloer uden dokumentpopup: {scrims}"
        return
    # Popuppen og dens sloer ligger over sidepanelet og klik-udenfor-laget.
    panel = names.index(f"con{tag}EditorPanel")
    outside = names.index(f"img{tag}EditorOutside")
    for n in scrims + [f"con{tag}AttModal"]:
        assert names.index(n) > max(panel, outside), f"{screen}: {n} ligger under panelet"


@pytest.mark.parametrize("screen,tag,docs", [s for s in SCREENS if s[2]])
def test_docs_state_cleared_when_panel_closes(screen, tag, docs):
    scr = _load(screen)
    clear = f"Set(var{tag}DocsId, Blank())"
    assert clear in _prop(scr, "OnHidden"), f"{screen}: OnHidden glemmer ikke dokumenterne"
    for ctl in (f"img{tag}EditorOutside", f"btn{tag}EditorClose", f"btn{tag}EditorCancel",
                f"btn{tag}EditorPrevious", f"btn{tag}EditorNext"):
        node = _find(scr, ctl)
        assert node is not None, f"{screen}: {ctl} findes ikke"
        assert clear in _prop(node, "OnSelect"), f"{screen}: {ctl} glemmer ikke dokumenterne"
