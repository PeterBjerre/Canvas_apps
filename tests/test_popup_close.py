# -*- coding: utf-8 -*-
"""Popuppernes luk i hele BIO SAP (issue #237, #343).

Hver popup har EET X, oeverst til hoejre: sidste kontrol i popuppens
hoved, som er popuppens foerste barn og ligger uden for det, der scroller.
X'et er det samme som sidepanelernes (icon_button med icons.CLOSE). Ingen
popup har en Close- eller Cancel-knap med tekst, og ingen bund er tom.

Bekraeftelserne (navne med "Confirm") har ogsaa X'et oeverst; bunden har
kun handlingen. Fjern-bekraeftelsen inde i dokumentpopuppen (doc_upload,
"...RemoveCancel") er et ja/nej-valg - den lukker ikke popuppen.

Undtagelse (issue #429): Materials' Purchase order text er en lille
editor og har Cancel og Save i bunden som sidepanelet. X'et er der stadig.

Undtagelse (issue #450): Reset-bekraeftelserne (...ResetConfirmModal) har
Cancel (sikker) og Reset (destruktiv) i bunden, som issuet kraever. X'et
er der stadig."""
import glob
import os

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENS = sorted(glob.glob(os.path.join(ROOT, "BIO SAP App", "Screen*.pa.yaml")))
BUTTONS = ("ModernButton", "Classic/Button")
# Popupper, der bevidst har en Cancel-knap ved siden af Save (issue #429).
CANCEL_SAVE_POPUPS = {"conMatPoModal",
                      # Slet et item: Cancel og Delete, som issue #457 kraever.
                      "conVhpItemDelConfirmModal",
                      # Object list: Cancel og Use selected (mockup 2026-10-21).
                      "conVhpObjListModal",
                      # Materials' Object list: Cancel og Apply selection (#513).
                      "conMatObjListModal"}


def _icon_close(v):
    # Et almindeligt X-ikon uden ramme (Image) er ogsaa en Close.
    return (v.get("Control") == "Image"
            and str((v.get("Properties") or {}).get("AccessibleLabel", "")).strip().lstrip("=") == '"Close"')


def _kids(node):
    for c in node.get("Children", []) or []:
        for n, v in c.items():
            yield n, v


def _walk(name, node, out, parent=None):
    out.append((name, node, parent))
    for n, v in _kids(node):
        _walk(n, v, out, name)


def _prop(node, key):
    return str((node.get("Properties") or {}).get(key, "")).strip().lstrip("=").strip()


def _popups():
    found = []
    for path in SCREENS:
        with open(path, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        for s in doc["Screens"].values():
            allc = []
            for n, v in _kids(s):
                _walk(n, v, allc)
            for name, node, _p in allc:
                if (node.get("Control", "").startswith("GroupContainer")
                        and "ExtraBold" in _prop(node, "DropShadow")):
                    found.append((os.path.basename(path), name, node))
    return found


POPUPS = _popups()
IDS = [f"{f}:{n}" for f, n, _ in POPUPS]


def _buttons(node):
    out = []
    _walk("root", node, out)
    return [(n, v, p) for n, v, p in out if v.get("Control") in BUTTONS or _icon_close(v)]


def test_popups_found():
    # Vaagt mod at testen stille finder nul popupper.
    assert len(POPUPS) >= 40
    names = {n for _, n, _ in POPUPS}
    for must in ("conVhpObjListModal", "conVhpPickerModal",
                 "conKksPickModal", "conVhpNotesModal"):
        assert must in names


def _closes(node):
    """Popuppens X'er: Image-kontroller, hvis tooltip er "Close"."""
    out = []
    _walk("root", node, out)
    return [(n, v) for n, v, _ in out
            if v.get("Control") == "Image" and _prop(v, "Tooltip") in ('"Close"', '"Close without applying"')]


def _sidebar_x():
    """Sidepanelets X (btnEqEditorClose) - referencen for popuppernes X."""
    with open(os.path.join(ROOT, "BIO SAP App", "ScreenEquipment.pa.yaml"), encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    allc = []
    for s in doc["Screens"].values():
        for n, v in _kids(s):
            _walk(n, v, allc)
    return next(v for n, v, _ in allc if n == "btnEqEditorClose")


SIDEBAR_X = _sidebar_x()


@pytest.mark.parametrize("screen,name,node", POPUPS, ids=IDS)
def test_one_x_no_close_button(screen, name, node):
    # Issue #343: ingen Close- eller Cancel-knap med tekst; EET X.
    btns = _buttons(node)
    cancel_ok = name in CANCEL_SAVE_POPUPS or name.endswith("ResetConfirmModal")
    banned = ('"Close"',) if cancel_ok else ('"Close"', '"Cancel"')
    texts = [n for n, v, _ in btns if _prop(v, "Text") in banned
             and not n.endswith("RemoveCancel")]
    assert not texts, f"{name}: Close/Cancel-knapper med tekst: {texts}"
    xs = [n for n, _ in _closes(node)]
    assert len(xs) == 1, f"{name}: X'er {xs}"


@pytest.mark.parametrize("screen,name,node", POPUPS, ids=IDS)
def test_x_top_right_and_fixed(screen, name, node):
    # Hovedet er popuppens foerste barn; X er dets sidste barn.
    first_name, head = next(_kids(node))
    assert "Horizontal" in _prop(head, "LayoutDirection"), f"{name}: {first_name}"
    kids = list(_kids(head))
    last_name, last = kids[-1]
    assert (last_name, last) in _closes(node), f"{name}: sidste i hovedet er {last_name}"
    # Hovedet scroller ikke med indholdet.
    assert "Scroll" not in _prop(node, "LayoutOverflowY"), name
    assert "Scroll" not in _prop(head, "LayoutOverflowY"), name


@pytest.mark.parametrize("screen,name,node", POPUPS, ids=IDS)
def test_x_matches_sidebar(screen, name, node):
    # Samme X som sidepanelet: ikon, stoerrelse, hover og tryk (issue #343).
    # Et X, der slukkes midt i en gemning (DisplayMode), toner ud og har
    # ingen hover, mens det er slukket - dets Image og Fill er betingede.
    (_n, x), = _closes(node)
    for key in ("Width", "Height", "Fill", "BorderStyle", "ImagePosition",
                "AlignInContainer", "LayoutMinWidth", "RadiusTopLeft"):
        assert _prop(x, key) == _prop(SIDEBAR_X, key), f"{name}: {key}"
    if "DisplayMode" in (x.get("Properties") or {}):
        assert "C.'row-hover'" in _prop(x, "HoverFill"), name
        assert "M6 6l12 12M18 6L6 18" in _prop(x, "Image"), name
    else:
        for key in ("Image", "HoverFill", "PressedFill"):
            assert _prop(x, key) == _prop(SIDEBAR_X, key), f"{name}: {key}"


@pytest.mark.parametrize("screen,name,node", POPUPS, ids=IDS)
def test_no_empty_footer(screen, name, node):
    out = []
    _walk("root", node, out)
    for n, v, _ in out:
        if n.endswith(("Footer", "Foot")):
            assert list(_kids(v)), f"{name}: tom bund {n}"


def test_cancel_logic_moved_to_close():
    # X koerer den oprydning, Cancel gjorde - ventende valg kasseres.
    by = {}
    for _f, _n, node in POPUPS:
        out = []
        _walk("root", node, out)
        for n, v, _ in out:
            if v.get("Control") in BUTTONS + ("Image",):
                by[n] = _prop(v, "OnSelect")
    assert "Clear(colVhpObjDraft)" in by["btnVhpObjListClose"]
    assert "colVhpItemObjects" not in by["btnVhpObjListClose"]
    assert "Clear(colVhpPickerSelected)" in by["btnVhpPickerClose"]
    assert "Collect" not in by["btnVhpPickerClose"]
    # Apply, Use selected og Add selected lines er bevaret.
    for keep in ("btnVhpObjListUse", "btnVhpPickerAddSelected",
                 "btnVhpSubmitConfirm"):
        assert keep in by, keep
