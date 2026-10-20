# -*- coding: utf-8 -*-
"""
Reset spoerger foerst - ens i hele appen (issue #450).

Alle Reset-knapper (sidepanelerne i Materials, Equipment, Measuring Point
og Functional Location, og VH-planens Plan header og Item Editor) bruger
build_helpers.reset_click_fx og reset_confirm:

  - Knappen aabner bekraeftelsen, naar der er ugemte aendringer - ellers
    nulstiller den med det samme (ingen bekraeftelse uden aendringer).
  - Bekraeftelsen: "Reset changes?", at aendringerne kasseres og ikke kan
    gendannes, Cancel (neutral) og Reset (roed, destruktiv).
  - Foerst Reset i bekraeftelsen nulstiller, og den lukker popuppen FOER.

Power Fx kan ikke koeres her, saa testene laeser den GENEREREDE skaerm.

    python3 -m pytest tests/test_reset_confirm.py
"""
import os

import pytest

from conftest import ROOT

import test_material_objects as M

APP = os.path.join(ROOT, "BIO SAP App")


def _screen(name):
    return os.path.join(APP, f"Screen{name}.pa.yaml")


# (skaerm, Reset-knap, bekraeftelsens praefiks, ventevariabel)
RESETS = [
    ("Material", "btnMatNew", "MatReset", "varMatResetAsk"),
    ("Equipment", "btnEqNew", "EqReset", "varEqResetAsk"),
    ("MeasuringPoint", "btnMpNew", "MpReset", "varMpResetAsk"),
    ("FunctionalLocation", "btnFlEditorReset", "FlRowReset", "varFlPanelResetAsk"),
    ("VhPlan", "btnVhpPlanReset", "VhpPlanReset", "varVhpPlanResetAsk"),
    ("VhPlan", "btnVhpResetItem", "VhpItemReset", "varVhpItemResetAsk"),
]
IDS = [r[1] for r in RESETS]


def test_every_reset_button_is_covered():
    """Vaagt: en ny Reset-knap skal ogsaa spoerge (og staa i RESETS)."""
    known = {r[1] for r in RESETS}
    for name in os.listdir(APP):
        if not (name.startswith("Screen") and name.endswith(".pa.yaml")):
            continue
        import yaml
        doc = yaml.safe_load(open(os.path.join(APP, name), encoding="utf-8"))

        def walk(node):
            for c in node.get("Children", []) or []:
                for n, v in c.items():
                    props = v.get("Properties") or {}
                    if (v.get("Control") == "ModernButton"
                            and str(props.get("Text", "")).strip().lstrip("=") == '"Reset"'
                            and not n.endswith("Confirm")):
                        assert n in known, f"{name}: {n} er en Reset uden bekraeftelse"
                    walk(v)
        for s in doc["Screens"].values():
            walk(s)


@pytest.mark.parametrize("screen,btn,prefix,ask", RESETS, ids=IDS)
def test_button_asks_only_when_there_are_changes(screen, btn, prefix, ask):
    click = M._prop(btn, "OnSelect", _screen(screen))
    # If(<aendret>, Set(ask, true), <nulstil med det samme>)
    assert click.startswith("If(\n")
    assert f",\n    Set({ask}, true),\n" in click
    dirty = click[len("If(\n    "):click.index(f",\n    Set({ask}, true)")]
    # Bekraeftelsen vises kun, mens der stadig er noget at kassere.
    vis = M._prop(f"con{prefix}ConfirmModal", "Visible", _screen(screen))
    assert vis.startswith(f"IfError({ask}, false) && (")
    flat = lambda t: " ".join(t.split())
    assert flat(dirty) in flat(vis)


@pytest.mark.parametrize("screen,btn,prefix,ask", RESETS, ids=IDS)
def test_dialog_text_and_actions(screen, btn, prefix, ask):
    path = _screen(screen)
    assert M._prop(f"txt{prefix}ConfirmTitle", "Text", path) == '"Reset changes?"'
    msg = M._prop(f"txt{prefix}ConfirmText", "Text", path)
    assert "will be discarded and cannot be recovered" in msg
    footer = [list(c)[0] for c in M._ctrl(f"con{prefix}ConfirmFooter", path)["Children"]]
    assert footer == [f"btn{prefix}ConfirmKeep", f"btn{prefix}Confirm"]
    # Cancel: neutral og goer intet andet end at lukke.
    keep = M._ctrl(f"btn{prefix}ConfirmKeep", path)["Properties"]
    assert str(keep["Text"]).lstrip("=") == '"Cancel"'
    assert str(keep["OnSelect"]).lstrip("=") == f"Set({ask}, false)"
    assert "error" not in str(keep["BorderColor"])
    # Reset: destruktiv (roed kant og tekst, som sletningernes) og lukker
    # popuppen foer nulstillingen.
    ok = M._ctrl(f"btn{prefix}Confirm", path)["Properties"]
    assert str(ok["Text"]).lstrip("=") == '"Reset"'
    assert "error" in str(ok["BorderColor"])
    assert str(ok["OnSelect"]).lstrip("=").startswith(f"Set({ask}, false);\n")
    # X og et tryk paa sloeret lukker ogsaa uden at nulstille.
    assert M._prop(f"btn{prefix}ConfirmCancel", "OnSelect", path) == f"Set({ask}, false)"
    assert M._prop(f"con{prefix}ConfirmBackdrop", "OnSelect", path) == f"Set({ask}, false)"


def test_domain_reset_keeps_the_open_tab():
    """Brugeren bliver paa fanen (issue #450): Details, Objects eller
    Documents - indlaesningen saetter Details, saa fanen saettes tilbage."""
    for p, screen in (("Mat", "Material"), ("Eq", "Equipment")):
        reset = M._prop(f"btn{p}ResetConfirm", "OnSelect", _screen(screen))
        assert f"{{ keepTab: Coalesce(var{p}EditorTab, \"Details\") }}" in reset
        assert f"Set(var{p}EditorTab, keepTab)" in reset
        assert f"Set(var{p}DocsId, var{p}ActiveRowId)" in reset
    # Materials henter objektlisten igen, naar brugeren stod paa Objects.
    mat = M._prop("btnMatResetConfirm", "OnSelect", _screen("Material"))
    assert 'keepTab = "Objects"' in mat


def test_vhp_resets_stay_in_their_section():
    path = _screen("VhPlan")
    plan = M._prop("btnVhpPlanResetConfirm", "OnSelect", path)
    assert "Reset(drpVhpPlanType); Reset(drpVhpStrategy)" in plan
    assert "If(varVhpPlanCommitted, Set(varVhpPlanLocked, true))" in plan
    item = M._prop("btnVhpItemResetConfirm", "OnSelect", path)
    assert "RemoveIf(colVhpItemObjects, ItemId = varVhpActiveItemId)" in item
    assert "Reset(inpVhpItemShortText)" in item
    # Intet gemmes i SharePoint, og det aktive item skiftes ikke.
    for gone in ("Patch(", "Set(varVhpActiveItemId"):
        assert gone not in plan and gone not in item
    # Plan header: hvert felt sammenlignes med den gemte plan.
    click = M._prop("btnVhpPlanReset", "OnSelect", path)
    for ref in ("varVhpPlan.PlanType", "varVhpPlan.Plant", "inpVhpPlanText.Text",
                "varVhpPlan.SortField", "varVhpPlan.Cycle", "varVhpPlan.Unit",
                "dteVhpFirstCall.SelectedDate"):
        assert ref in click, ref
    # Item: felterne (som Submit) og objektlisten mod itemets gemte ObjectList.
    click = M._prop("btnVhpResetItem", "OnSelect", path)
    assert "inpVhpItemShortText.Text" in click
    assert "Split(it.ObjectList" in click
