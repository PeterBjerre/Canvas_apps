# -*- coding: utf-8 -*-
"""Issue #526: alle segmenterede vaelgere og knap-faner har EET faelles
udtryk (build_helpers.seg_style/seg_track og tokens seg-* i
design_tokens) - lys skinne, valgt = lyseblaa kant og moerkeblaa tekst,
ingen fyldt, moerkeblaa pille. Vaerdier og handlinger er uaendrede."""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import design_tokens as dt  # noqa: E402

APP = os.path.join(ROOT, "BIO SAP App")

# Skaerm -> segmenter/faner, der skal have det faelles udtryk.
EXPECTED = {
    "ScreenMdHub": ["conMdFltStatusOpen", "conMdFltStatusClosed", "conMdFltStatusAll",
                    "conMdFltViewMine", "conMdFltViewAll", "conMdViewMMine", "conMdViewMAll"],
    "ScreenMaterial": ["conMatEditorTabsDetails", "conMatEditorTabsObjects",
                       "conMatEditorTabsDocuments", "conMatStrategicPartSegNo",
                       "conMatStrategicPartSegYes", "conMatWearPartSegYes"],
    "ScreenEquipment": ["conEqEditorTabsDetails", "conEqEditorTabsDocuments"],
    "ScreenMeasuringPoint": ["conMpExistsInSapSegNo", "conMpExistsInSapSegYes"],
    "ScreenVhPlan": ["conVhpItemRevisionSegNo", "conVhpItemNonFlowSegZbow"],
    "ScreenIssueBoard": ["btnIbTabDetails", "btnIbTabActivity", "btnIbTabFiles"],
    "ScreenKks": ["btnKksKeyFunction", "btnKksKeyAggregate", "btnKksKeyComponent"],
    "ScreenFunctionalLocation": ["btnFlTab"],
}
# Faner uden skinne: de ikke valgte har en diskret kant.
STANDALONE = {"btnIbTabDetails", "btnIbTabActivity", "btnIbTabFiles", "btnKksKeyFunction",
              "btnKksKeyAggregate", "btnKksKeyComponent", "btnFlTab"}


def _walk(items, parent=None):
    for it in items or []:
        (n, b), = it.items()
        yield n, b, parent
        yield from _walk(b.get("Children"), (n, b))


def _screens():
    out = {}
    for f in glob.glob(os.path.join(APP, "Screen*.pa.yaml")):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        for sn, s in d["Screens"].items():
            out[sn] = {n: (b, p) for n, b, p in _walk(s.get("Children"))}
    return out


def _p(body, key):
    return str((body.get("Properties") or {}).get(key, "")).strip().lstrip("=").strip()


def test_tokens_in_both_themes_and_contrast_guarded():
    for name in ("seg-track-bg", "seg-on-fg", "seg-on-border"):
        assert name in dt.LIGHT and name in dt.DARK
    pairs = {(fg, bg) for fg, bg, _m in dt.CONTRAST}
    assert ("seg-on-fg", "seg-track-bg") in pairs
    assert ("text-muted", "seg-track-bg") in pairs
    assert ("seg-on-border", "seg-track-bg") in pairs


def test_every_switcher_uses_the_shared_style():
    screens = _screens()
    for sn, names in EXPECTED.items():
        ctrls = screens[sn]
        for n in names:
            body, parent = ctrls[n]
            assert body["Control"] == "ModernButton", n
            assert _p(body, "Appearance") == "ButtonAppearance.Outline", n
            border = _p(body, "BorderColor")
            assert border.startswith("If(") and "C.'seg-on-border'" in border, n
            idle = "C.'border-default'" if n in STANDALONE else "RGBA(0, 0, 0, 0)"
            assert border.endswith(f", {idle})"), (n, border)
            assert "C.'seg-on-fg'" in _p(body, "Color"), n
            assert "FontWeight.Semibold" in _p(body, "FontWeight"), n
            # Bloedt rundet, ikke en kapsel.
            assert _p(body, "RadiusTopLeft") == "If(LayoutRank < 2, 8, 6)", n
            if n not in STANDALONE:
                pb = parent[1]
                assert _p(pb, "Fill") == "C.'seg-track-bg'", n
                assert _p(pb, "BorderColor") == "C.'border-default'", n
                assert _p(pb, "RadiusTopLeft") == "If(LayoutRank < 2, 10, 8)", n


def test_no_switcher_is_a_filled_dark_pill_any_more():
    """Ingen knap med "selected" i sin etiket er Primary (den fyldte,
    moerkeblaa pille) - og ingen skinne har den gamle graablaa flade."""
    for sn, ctrls in _screens().items():
        for n, (body, parent) in ctrls.items():
            if body.get("Control") != "ModernButton":
                continue
            if '", selected"' in _p(body, "AccessibleLabel"):
                assert "ButtonAppearance.Primary" not in _p(body, "Appearance"), (sn, n)
                assert "C.'seg-on-border'" in _p(body, "BorderColor"), (sn, n)
                assert _p(parent[1], "Fill") != "C.'state-neutral-bg'", (sn, n)


def test_values_and_actions_are_unchanged():
    s = _screens()
    hub = s["ScreenMdHub"]
    assert _p(hub["conMdFltStatusClosed"][0], "OnSelect").startswith(
        'Set(varMdStatusMode, "done")')
    assert _p(hub["conMdFltViewAll"][0], "OnSelect").startswith(
        'Set(varMdView, "queue"); Set(varMdDomain, "")')
    mat = s["ScreenMaterial"]
    assert _p(mat["conMatStrategicPartSegYes"][0], "OnSelect") == 'Set(varMatFStrategicPart, "Yes")'
    # Skrivebeskyttelsen foelger stadig raekken.
    assert _p(mat["conMatStrategicPartSegYes"][0], "DisplayMode").startswith(
        "If(varMatViewOnly || ")
    assert 'Set(varMatEditorTab, "Documents")' in _p(mat["conMatEditorTabsDocuments"][0], "OnSelect")
    # Mobilgrenene (#508) er der stadig: 40 px hoeje segmenter paa en telefon.
    assert _p(mat["conMatIsStockItemSegYes"][0], "Height") == "If(LayoutRank < 2, 40, 30)"
