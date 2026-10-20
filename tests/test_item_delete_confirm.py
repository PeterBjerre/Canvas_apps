# -*- coding: utf-8 -*-
"""VH-plan: Delete paa et items kort spoerger foerst (issue #457).

Der er kun EEN Delete paa et item - kortets i Items-listen. Item Editorens
"Delete item" er fjernet. Kortets knap sletter intet selv; den aabner en
bekraeftelse med en tydelig advarsel, Cancel og Delete. Foerst Delete DER
sletter itemet og alt, der haenger paa det."""
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")


def _all():
    with open(SCREEN, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    out = {}

    def walk(n, v):
        out[n] = v
        for c in v.get("Children", []) or []:
            for k, w in c.items():
                walk(k, w)
    for s in doc["Screens"].values():
        for c in s.get("Children", []) or []:
            for k, v in c.items():
                walk(k, v)
    return out


CTRLS = _all()


def _p(name, key):
    return str((CTRLS[name].get("Properties") or {}).get(key, "")).strip().lstrip("=").strip()


def test_editor_has_no_delete():
    assert "btnVhpEditorDelete" not in CTRLS
    assert not [n for n in CTRLS if n.startswith("btnVhpEditor") and "Delete" in n]


def test_card_delete_only_opens_the_confirmation():
    fx = _p("btnVhpRemoveItem", "OnSelect")
    assert "Set(varVhpItemDelId, ThisItem.ItemId)" in fx
    assert "Set(varVhpItemDelAsk, true)" in fx
    assert "RemoveIf" not in fx


def test_confirmation_warns_and_has_cancel_and_delete():
    assert _p("txtVhpItemDelConfirmTitle", "Text") == '"Delete item?"'
    msg = _p("txtVhpItemDelConfirmText", "Text")
    assert "permanently deleted" in msg
    for what in ("task list", "operations", "materials", "documents", "object list"):
        assert what in msg
    assert _p("btnVhpItemDelConfirmKeep", "Text") == '"Cancel"'
    assert _p("btnVhpItemDelConfirm", "Text") == '"Delete"'
    # Cancel og X sletter intet.
    for n in ("btnVhpItemDelConfirmKeep", "btnVhpItemDelConfirmCancel"):
        assert "RemoveIf" not in _p(n, "OnSelect")
        assert "Set(varVhpItemDelAsk, false)" in _p(n, "OnSelect")
    # Cancel foer Delete i foden.
    foot = [list(c)[0] for c in CTRLS["conVhpItemDelConfirmFooter"]["Children"]]
    assert foot == ["btnVhpItemDelConfirmKeep", "btnVhpItemDelConfirm"]


def test_delete_removes_the_item_and_everything_on_it():
    fx = _p("btnVhpItemDelConfirm", "OnSelect")
    assert "{ id: varVhpItemDelId," in fx
    for col in ("colVhpOperations", "colVhpItemObjects", "colVhpMaterials",
                "colVhpAttachments", "colVhpSectionLocks", "colVhpItems"):
        assert f"RemoveIf({col}, ItemId = id)" in fx, col
    # Popuppen lukkes og glemmer itemet.
    assert fx.index("Set(varVhpItemDelAsk, false)") < fx.index("RemoveIf(")
    assert fx.rstrip().endswith("Set(varVhpItemDelId, Blank())")


def test_confirmation_hidden_in_view_mode_and_when_item_is_gone():
    vis = _p("conVhpItemDelConfirmModal", "Visible")
    assert "varVhpViewOnly" in vis
    assert "LookUp(colVhpItems, ItemId = varVhpItemDelId)" in vis
