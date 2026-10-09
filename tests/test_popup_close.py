# -*- coding: utf-8 -*-
"""Popuppernes luk-knap i hele BIO SAP (issue #237).

Hver popup har EEN Close, oeverst til hoejre: sidste knap i popuppens
hoved, som er popuppens foerste barn og ligger uden for det, der scroller.
Ingen popup har baade Close og Cancel, og ingen bund er tom.

Bekraeftelser (navne med "Confirm") er et ja/nej-valg: Close er deres
nej-knap i bunden ved siden af handlingen, og den er stadig den eneste.
Fjern-bekraeftelsen inde i dokumentpopuppen (doc_upload, "...RemoveCancel")
er ogsaa et ja/nej-valg - den lukker ikke popuppen."""
import glob
import os

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENS = sorted(glob.glob(os.path.join(ROOT, "BIO SAP App", "Screen*.pa.yaml")))
BUTTONS = ("ModernButton", "Classic/Button")


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
    return [(n, v, p) for n, v, p in out if v.get("Control") in BUTTONS]


def test_popups_found():
    # Vaagt mod at testen stille finder nul popupper.
    assert len(POPUPS) >= 40
    names = {n for _, n, _ in POPUPS}
    for must in ("conVhpObjListModal", "conVhpPickerModal", "conFlClsModal",
                 "conFlPopModal", "conKksPickModal", "conVhpNotesModal"):
        assert must in names


@pytest.mark.parametrize("screen,name,node", POPUPS, ids=IDS)
def test_one_close_no_cancel(screen, name, node):
    btns = _buttons(node)
    closes = [n for n, v, _ in btns if _prop(v, "Text") == '"Close"']
    cancels = [n for n, v, _ in btns if _prop(v, "Text") == '"Cancel"'
               and not n.endswith("RemoveCancel")]
    assert len(closes) == 1, f"{name}: Close-knapper {closes}"
    assert not cancels, f"{name}: Cancel ved siden af Close: {cancels}"


@pytest.mark.parametrize("screen,name,node",
                         [p for p in POPUPS if "Confirm" not in p[1]],
                         ids=[i for i in IDS if "Confirm" not in i])
def test_close_top_right_and_fixed(screen, name, node):
    # Hovedet er popuppens foerste barn; Close er dets sidste barn.
    first_name, head = next(_kids(node))
    assert "Horizontal" in _prop(head, "LayoutDirection"), f"{name}: {first_name}"
    kids = list(_kids(head))
    last_name, last = kids[-1]
    assert last.get("Control") in BUTTONS and _prop(last, "Text") == '"Close"', \
        f"{name}: sidste i hovedet er {last_name}"
    # Hovedet scroller ikke med indholdet.
    assert "Scroll" not in _prop(node, "LayoutOverflowY"), name
    assert "Scroll" not in _prop(head, "LayoutOverflowY"), name


@pytest.mark.parametrize("screen,name,node", POPUPS, ids=IDS)
def test_no_empty_footer(screen, name, node):
    out = []
    _walk("root", node, out)
    for n, v, _ in out:
        if n.endswith(("Footer", "Foot")):
            assert list(_kids(v)), f"{name}: tom bund {n}"


def test_cancel_logic_moved_to_close():
    # Close koerer den oprydning, Cancel gjorde - ventende valg kasseres.
    by = {}
    for _f, _n, node in POPUPS:
        for n, v, _ in _buttons(node):
            by[n] = _prop(v, "OnSelect")
    assert "Clear(colVhpObjDraft)" in by["btnVhpObjListClose"]
    assert "colVhpItemObjects" not in by["btnVhpObjListClose"]
    assert "Clear(colVhpPickerSelected)" in by["btnVhpPickerClose"]
    assert "Collect" not in by["btnVhpPickerClose"]
    # Apply, Use selected og Add selected lines er bevaret.
    for keep in ("btnFlClsApply", "btnVhpObjListUse", "btnVhpPickerAddSelected",
                 "btnVhpSubmitConfirm"):
        assert keep in by, keep
